import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from documents.models import Document, DocumentChunk
from subjects.models import Subject
from .exceptions import QuizGenerationError, QuizPersistenceError
from .models import Quiz, QuizAttempt
from .services.quiz_generator import QuizGenerator
from .services.quiz_persister import QuizPersister
from .tests import FakeLLM, make_payload


class QuizRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner")
        cls.other = User.objects.create_user("other")
        cls.subject = Subject.objects.create(user=cls.owner, name="Django")
        cls.document = Document.objects.create(user=cls.owner, subject=cls.subject, title="Django notes")
        cls.chunk = DocumentChunk.objects.create(document=cls.document, chunk_index=0, content="Django framework")
        cls.other_document = Document.objects.create(user=cls.other, subject=cls.subject, title="Private document")
        cls.foreign_chunk = DocumentChunk.objects.create(document=cls.other_document, chunk_index=0, content="Private")

    def setUp(self):
        self.client.force_login(self.owner)

    def test_generation_and_persistence_keep_valid_source_ids(self):
        payload = make_payload(1)
        payload["questions"][0]["source_chunk_ids"] = [self.chunk.pk]
        llm = FakeLLM(json.dumps(payload))
        data = QuizGenerator(llm=llm).generate(self.document)
        self.assertIn(f"[Chunk ID: {self.chunk.pk}]", llm.prompts[0])
        quiz = QuizPersister().save(self.document, self.owner, data)
        self.assertEqual(quiz.questions.get().source_chunk_ids, [self.chunk.pk])
        attempt = QuizAttempt.objects.create(quiz=quiz, user=self.owner, score=0, total_questions=1)
        response = self.client.get(reverse("quizzes:quiz_result", args=[attempt.pk]))
        self.assertContains(response, "Supporting study excerpts")
        self.assertContains(response, self.chunk.content)

    def test_generation_rejects_foreign_or_missing_source_ids(self):
        for sources in [[], [self.foreign_chunk.pk], [True], "invalid"]:
            payload = make_payload(1)
            payload["questions"][0]["source_chunk_ids"] = sources
            llm = FakeLLM(json.dumps(payload), json.dumps(payload))
            with self.subTest(sources=sources), self.assertRaises(QuizGenerationError):
                QuizGenerator(llm=llm).generate(self.document)
        self.assertFalse(Quiz.objects.exists())

    def test_non_string_difficulty_is_rejected_without_crashing(self):
        for difficulty in [[], {}, None, 42]:
            payload = make_payload(1)
            payload["questions"][0]["difficulty"] = difficulty
            payload["questions"][0]["source_chunk_ids"] = [self.chunk.pk]
            llm = FakeLLM(json.dumps(payload), json.dumps(payload))
            with self.subTest(difficulty=difficulty), self.assertRaises(QuizGenerationError):
                QuizGenerator(llm=llm).generate(self.document)

    def test_persistence_rejects_sources_outside_document_and_foreign_owner(self):
        old = QuizPersister().save(self.document, self.owner, make_payload(1))
        payload = make_payload(1)
        payload["questions"][0]["source_chunk_ids"] = [self.foreign_chunk.pk]
        with self.assertRaises(QuizPersistenceError):
            QuizPersister().save(self.document, self.owner, payload)
        with self.assertRaises(QuizPersistenceError):
            QuizPersister().save(self.document, self.other, make_payload(1))
        old.refresh_from_db()
        self.assertTrue(old.is_active)
        self.assertEqual(Quiz.objects.count(), 1)

    @override_settings(GEMINI_API_KEY="")
    def test_missing_api_key_is_handled(self):
        response = self.client.post(reverse("documents:document_generate_quiz", args=[self.document.pk]), follow=True)
        self.assertContains(response, "Could not generate quiz")
        self.assertFalse(Quiz.objects.exists())

    def test_provider_failure_does_not_include_raw_material_in_error(self):
        class FailedLLM:
            def generate(self, prompt):
                raise RuntimeError("private-token-and-study-content")
        with self.assertLogs("quizzes.services.quiz_generator", level="WARNING") as logs:
            with self.assertRaises(QuizGenerationError) as caught:
                QuizGenerator(llm=FailedLLM()).generate(self.document)
        self.assertNotIn("private-token", str(caught.exception))
        self.assertNotIn("private-token", " ".join(logs.output))

    def test_document_links_only_active_quiz_and_old_result_stays_readable(self):
        old = QuizPersister().save(self.document, self.owner, make_payload(1))
        attempt = QuizAttempt.objects.create(quiz=old, user=self.owner, score=1, total_questions=1)
        current = QuizPersister().save(self.document, self.owner, make_payload(1))
        response = self.client.get(reverse("documents:document_detail", args=[self.document.pk]))
        self.assertContains(response, reverse("quizzes:quiz_detail", args=[current.pk]))
        self.assertNotContains(response, f'href="{reverse("quizzes:quiz_detail", args=[old.pk])}"')
        response = self.client.get(reverse("quizzes:quiz_result", args=[attempt.pk]))
        self.assertContains(response, "quiz has been replaced")
        self.assertNotContains(response, reverse("quizzes:quiz_take", args=[old.pk]))


class ExistingQuizAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner")
        cls.other = User.objects.create_user("other")
        subject = Subject.objects.create(user=cls.owner, name="Subject")
        document = Document.objects.create(user=cls.owner, subject=subject, title="Document")
        cls.quiz = QuizPersister().save(document, cls.owner, make_payload(2))
        foreign_document = Document.objects.create(user=cls.other, subject=subject, title="Private")
        cls.foreign = QuizPersister().save(foreign_document, cls.other, make_payload(1))

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.list_url = reverse("quiz_api:quiz-list")
        self.detail_url = reverse("quiz_api:quiz-detail", args=[self.quiz.pk])
        self.attempt_url = reverse("quiz_api:quiz-attempt", args=[self.quiz.pk])

    def test_anonymous_access_denied(self):
        self.api.force_authenticate(None)
        self.assertIn(self.api.get(self.list_url).status_code, [401, 403])
        self.assertIn(self.api.get(self.detail_url).status_code, [401, 403])
        self.assertIn(self.api.post(self.attempt_url, {}, format="json").status_code, [401, 403])

    def test_list_is_paginated_private_and_does_not_reveal_answer_hints(self):
        data = self.api.get(self.list_url).json()
        self.assertEqual(data["count"], 1)
        self.assertEqual([q["id"] for q in data["results"]], [self.quiz.pk])
        question = data["results"][0]["questions"][0]
        self.assertNotIn("correct_choice_index", question)
        self.assertNotIn("explanation", question)
        self.assertEqual(len(question["choices"]), 4)

    def test_foreign_and_inactive_quizzes_are_inaccessible(self):
        for pk in [self.foreign.pk, self.quiz.pk]:
            if pk == self.quiz.pk:
                Quiz.objects.filter(pk=pk).update(is_active=False)
            self.assertEqual(self.api.get(reverse("quiz_api:quiz-detail", args=[pk])).status_code, 404)
            self.assertEqual(self.api.post(reverse("quiz_api:quiz-attempt", args=[pk]), {"answers": {"1": 0}}, format="json").status_code, 404)
        self.assertFalse(QuizAttempt.objects.exists())

    def test_submission_scores_on_server_and_records_missing_invalid_answers(self):
        first, second = list(self.quiz.questions.all())
        response = self.api.post(self.attempt_url, {
            "answers": {str(first.pk): 0, str(second.pk): 99, "99999": 0},
            "score": 999, "total_questions": 999, "is_correct": True,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["score"], 1)
        self.assertEqual(response.json()["total_questions"], 2)
        self.assertEqual(response.json()["percentage"], 50)
        attempt = QuizAttempt.objects.get()
        self.assertEqual(attempt.user, self.owner)
        self.assertEqual(attempt.answers[1]["chosen_index"], -1)
        response = self.api.post(self.attempt_url, {"answers": {str(first.pk): 0}}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["score"], 1)
        self.assertEqual(response.json()["answers"][1]["chosen_index"], -1)

    def test_bad_input_rejected_without_attempt(self):
        for payload in [{}, {"answers": {}}, {"answers": []},
                        {"answers": {"not-an-id": 0}}, {"answers": {"1": "bad"}}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.api.post(self.attempt_url, payload, format="json").status_code, 400)
        self.assertFalse(QuizAttempt.objects.exists())
