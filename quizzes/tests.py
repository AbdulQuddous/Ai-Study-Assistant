import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from documents.models import Document
from quizzes.exceptions import (
    QuizGenerationError,
    QuizPersistenceError,
    QuizScoringError,
)
from quizzes.models import Choice, Question, Quiz, QuizAttempt
from quizzes.services.quiz_generator import (
    QuizGenerator,
    extract_json,
    validate_quiz_payload,
)
from quizzes.services.quiz_persister import QuizPersister
from quizzes.services.quiz_scorer import QuizScorer
from subjects.models import Subject

User = get_user_model()


def make_document(user, subject=None):
    """
    Create a Document for testing.

    Document requires a subject FK, so if the caller does not pass one,
    create a Subject owned by the same user.
    """
    if subject is None:
        subject = Subject.objects.create(
            user=user,
            name=f"Subject for {user.username}",
        )
    return Document.objects.create(
        user=user,
        subject=subject,
        title="Doc",
    )


def make_payload(n=2):
    return {
        "title": "Sample",
        "description": "Desc",
        "questions": [
            {
                "text": f"Question {i}?",
                "explanation": "Because.",
                "difficulty": "easy",
                "choices": ["A", "B", "C", "D"],
                "correct_choice_index": i % 4,
            }
            for i in range(n)
        ],
    }


class FakeLLM:
    model_name = "fake-model"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.responses.pop(0)


class StubGenerator(QuizGenerator):
    def __init__(self, llm, chunks):
        super().__init__(llm=llm)
        self._chunks = chunks

    def _load_chunks(self, document):
        return self._chunks


def chunks(n, size=10):
    return [
        SimpleNamespace(content=f"c{i}-" + "x" * size)
        for i in range(n)
    ]

class StubGenerator(QuizGenerator):
    def __init__(self, llm, chunks):
        super().__init__(llm=llm)
        self._chunks = chunks

    def _load_chunks(self, document):
        return self._chunks


def chunks(n, size=10):
    return [SimpleNamespace(content=f"c{i}-" + "x" * size) for i in range(n)]


@override_settings(QUIZ_DEFAULT_QUESTION_COUNT=5, QUIZ_MAX_QUESTION_COUNT=20,
                   QUIZ_MAX_CONTEXT_CHARS=12000, QUIZ_CHOICES_PER_QUESTION=4)
class QuizGeneratorTests(TestCase):
    def test_valid_response(self):
        llm = FakeLLM(json.dumps(make_payload(3)))
        data = StubGenerator(llm, chunks(10)).generate(None, num_questions=3)
        self.assertEqual(len(data["questions"]), 3)

    def test_fenced_and_prose_wrapped_json(self):
        raw = "Here you go:\n```json\n" + json.dumps(make_payload(1)) + "\n```"
        self.assertEqual(extract_json(raw)["title"], "Sample")

    def test_retry_succeeds(self):
        llm = FakeLLM("not json", json.dumps(make_payload(1)))
        data = StubGenerator(llm, chunks(4)).generate(None, num_questions=2)
        self.assertEqual(len(llm.prompts), 2)
        self.assertIn("did not match the required format", llm.prompts[1])
        self.assertEqual(len(data["questions"]), 1)

    def test_retry_fails(self):
        llm = FakeLLM("bad", "worse")
        with self.assertRaises(QuizGenerationError):
            StubGenerator(llm, chunks(4)).generate(None, num_questions=2)
        self.assertEqual(len(llm.prompts), 2)

    def test_no_chunks(self):
        with self.assertRaises(QuizGenerationError):
            StubGenerator(FakeLLM(), []).generate(None)

    def test_more_than_requested_is_truncated(self):
        llm = FakeLLM(json.dumps(make_payload(5)))
        data = StubGenerator(llm, chunks(10)).generate(None, num_questions=3)
        self.assertEqual(len(data["questions"]), 3)

    def test_fewer_than_requested_accepted(self):
        llm = FakeLLM(json.dumps(make_payload(1)))
        data = StubGenerator(llm, chunks(10)).generate(None, num_questions=5)
        self.assertEqual(len(data["questions"]), 1)

    def test_even_sampling_spans_document(self):
        gen = StubGenerator(FakeLLM(), [])
        ctx = gen._build_context(chunks(7), 3)  # desired = 6 of 7
        self.assertIn("c0-", ctx)
        self.assertIn("c6-", ctx)

    @override_settings(QUIZ_MAX_CONTEXT_CHARS=100)
    def test_context_capped_per_chunk(self):
        gen = StubGenerator(FakeLLM(), [])
        ctx = gen._build_context(chunks(10, size=500), 5)
        self.assertLessEqual(len(ctx), 100 + 9 * len("\n\n---\n\n"))

    def test_default_question_count_used(self):
        llm = FakeLLM(json.dumps(make_payload(1)))
        StubGenerator(llm, chunks(10)).generate(None)
        self.assertIn("up to 5", llm.prompts[0])

    def test_validation_rejects_bad_payloads(self):
        bad = make_payload(1)
        bad["questions"][0]["choices"] = ["A", "A", "B", "C"]
        with self.assertRaises(QuizGenerationError):
            validate_quiz_payload(bad, 5)
        bad = make_payload(1)
        bad["questions"][0]["correct_choice_index"] = 4
        with self.assertRaises(QuizGenerationError):
            validate_quiz_payload(bad, 5)
        bad = make_payload(1)
        bad["questions"][0]["difficulty"] = "impossible"
        with self.assertRaises(QuizGenerationError):
            validate_quiz_payload(bad, 5)


class QuizPersisterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pw")
        self.doc = make_document(self.user)

    def test_creates_everything(self):
        quiz = QuizPersister().save(self.doc, self.user, make_payload(3), model_used="m")
        self.assertEqual(quiz.question_count, 3)
        self.assertEqual(quiz.model_used, "m")
        self.assertEqual(Question.objects.filter(quiz=quiz).count(), 3)
        self.assertEqual(Choice.objects.filter(question__quiz=quiz).count(), 12)
        self.assertEqual(list(quiz.questions.values_list("order", flat=True)), [1, 2, 3])
        first = quiz.questions.first()
        self.assertEqual(list(first.choices.values_list("order", flat=True)), [0, 1, 2, 3])
        self.assertEqual(first.source_chunk_ids, [])

    def test_deactivates_previous(self):
        old = QuizPersister().save(self.doc, self.user, make_payload(1))
        new = QuizPersister().save(self.doc, self.user, make_payload(1))
        old.refresh_from_db()
        self.assertFalse(old.is_active)
        self.assertTrue(new.is_active)

    def test_rollback_keeps_old_active(self):
        old = QuizPersister().save(self.doc, self.user, make_payload(1))
        broken = make_payload(2)
        del broken["questions"][1]["choices"]
        with self.assertRaises(QuizPersistenceError):
            QuizPersister().save(self.doc, self.user, broken)
        old.refresh_from_db()
        self.assertTrue(old.is_active)
        self.assertEqual(Quiz.objects.count(), 1)

    def test_empty_questions_rejected(self):
        with self.assertRaises(QuizPersistenceError):
            QuizPersister().save(self.doc, self.user, {"title": "t", "questions": []})

    def test_duplicate_titles_allowed(self):
        QuizPersister().save(self.doc, self.user, make_payload(1))
        QuizPersister().save(self.doc, self.user, make_payload(1))
        self.assertEqual(Quiz.objects.count(), 2)


class QuizScorerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pw")
        self.quiz = QuizPersister().save(make_document(self.user), self.user, make_payload(4))
        self.qs = list(self.quiz.questions.all())  # correct indices 0,1,2,3

    def answers(self, idxs):
        return {q.id: i for q, i in zip(self.qs, idxs)}

    def test_all_correct(self):
        r = QuizScorer().score(self.quiz, self.answers([0, 1, 2, 3]))
        self.assertEqual((r["score"], r["total_questions"]), (4, 4))

    def test_all_wrong(self):
        self.assertEqual(QuizScorer().score(self.quiz, self.answers([3, 3, 3, 0]))["score"], 0)

    def test_partial(self):
        self.assertEqual(QuizScorer().score(self.quiz, self.answers([0, 1, 0, 0]))["score"], 2)

    def test_missing_counts_wrong(self):
        r = QuizScorer().score(self.quiz, {})
        self.assertEqual(r["score"], 0)
        self.assertTrue(all(a["chosen_index"] == -1 for a in r["answers"]))

    def test_malformed_values_coerced(self):
        r = QuizScorer().score(self.quiz, self.answers([99, "x", None, True]))
        self.assertTrue(all(a["chosen_index"] == -1 for a in r["answers"]))

    def test_extra_keys_and_client_correctness_ignored(self):
        subs = self.answers([0, 1, 2, 3])
        subs[999999] = 0
        subs["is_correct"] = True
        r = QuizScorer().score(self.quiz, subs)
        self.assertEqual(len(r["answers"]), 4)

    def test_empty_quiz_raises(self):
        self.quiz.questions.all().delete()
        with self.assertRaises(QuizScoringError):
            QuizScorer().score(self.quiz, {})


class QuizViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pw")
        self.other = User.objects.create_user("u2", password="pw")
        self.doc = make_document(self.user)
        self.quiz = QuizPersister().save(self.doc, self.user, make_payload(2))
        self.client.login(username="u1", password="pw")

    def post_answers(self, quiz, idxs):
        data = {f"q_{q.id}": i for q, i in zip(quiz.questions.all(), idxs)}
        return self.client.post(reverse("quizzes:quiz_take", args=[quiz.pk]), data)

    def test_login_required(self):
        self.client.logout()
        for name, args in [("quiz_list", []), ("quiz_detail", [self.quiz.pk]),
                           ("quiz_take", [self.quiz.pk])]:
            r = self.client.get(reverse(f"quizzes:{name}", args=args))
            self.assertEqual(r.status_code, 302, name)

    def test_cross_user_404(self):
        self.client.logout()
        self.client.login(username="u2", password="pw")
        for name in ("quiz_detail", "quiz_take"):
            r = self.client.get(reverse(f"quizzes:{name}", args=[self.quiz.pk]))
            self.assertEqual(r.status_code, 404, name)

    def test_cross_user_result_404(self):
        self.post_answers(self.quiz, [0, 1])
        attempt = QuizAttempt.objects.get()
        self.client.logout()
        self.client.login(username="u2", password="pw")
        r = self.client.get(reverse("quizzes:quiz_result", args=[attempt.pk]))
        self.assertEqual(r.status_code, 404)

    def test_list_and_detail(self):
        self.assertContains(self.client.get(reverse("quizzes:quiz_list")), "Sample")
        self.assertContains(self.client.get(reverse("quizzes:quiz_detail", args=[self.quiz.pk])), "Start Quiz")

    def test_inactive_quiz_404(self):
        Quiz.objects.filter(pk=self.quiz.pk).update(is_active=False)
        for name in ("quiz_detail", "quiz_take"):
            self.assertEqual(self.client.get(reverse(f"quizzes:{name}", args=[self.quiz.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("quizzes:quiz_list")), "Sample")

    def test_take_get_renders_radios(self):
        r = self.client.get(reverse("quizzes:quiz_take", args=[self.quiz.pk]))
        q = self.quiz.questions.first()
        self.assertContains(r, f'name="q_{q.id}"')

    def test_submit_creates_attempt_and_redirects(self):
        r = self.post_answers(self.quiz, [0, 1])
        attempt = QuizAttempt.objects.get()
        self.assertRedirects(r, reverse("quizzes:quiz_result", args=[attempt.pk]))
        self.assertEqual(attempt.score, 2)
        self.assertContains(self.client.get(r.url), "2/2")

    def test_submit_malformed_answers(self):
        q1, q2 = self.quiz.questions.all()
        r = self.client.post(reverse("quizzes:quiz_take", args=[self.quiz.pk]),
                             {f"q_{q1.id}": "junk", f"q_{q2.id}": "99"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(QuizAttempt.objects.get().score, 0)

    def test_generate_requires_post(self):
        r = self.client.get(reverse("documents:document_generate_quiz", args=[self.doc.pk]))
        self.assertEqual(r.status_code, 405)

    def test_generate_cross_user_404(self):
        self.client.logout()
        self.client.login(username="u2", password="pw")
        r = self.client.post(reverse("documents:document_generate_quiz", args=[self.doc.pk]))
        self.assertEqual(r.status_code, 404)

    @patch("quizzes.views.QuizGenerator")
    def test_generate_success(self, gen_cls):
        gen = gen_cls.return_value
        gen.generate.return_value = make_payload(2)
        gen.model_used = "fake"
        r = self.client.post(reverse("documents:document_generate_quiz", args=[self.doc.pk]))
        new = Quiz.objects.filter(is_active=True).get()
        self.assertRedirects(r, reverse("quizzes:quiz_detail", args=[new.pk]))
        self.assertEqual(Quiz.objects.filter(is_active=False).count(), 1)

    @patch("quizzes.views.QuizGenerator")
    def test_generate_error_path(self, gen_cls):
        gen_cls.return_value.generate.side_effect = QuizGenerationError("boom")
        r = self.client.post(reverse("documents:document_generate_quiz", args=[self.doc.pk]),
                             follow=False)
        self.assertRedirects(r, reverse("documents:document_detail", args=[self.doc.pk]),
                             fetch_redirect_response=False)
        self.assertTrue(Quiz.objects.get(pk=self.quiz.pk).is_active)


class QuizIntegrationTests(TestCase):
    """generate -> take -> submit -> result, with the LLM mocked."""

    def setUp(self):
        self.user = User.objects.create_user("u1", password="pw")
        self.doc = make_document(self.user)
        self.client.login(username="u1", password="pw")

    @patch("quizzes.views.QuizGenerator")
    def test_full_flow(self, gen_cls):
        gen_cls.return_value.generate.return_value = make_payload(3)
        gen_cls.return_value.model_used = "fake"
        r = self.client.post(reverse("documents:document_generate_quiz", args=[self.doc.pk]))
        quiz = Quiz.objects.get()
        self.assertEqual(r.status_code, 302)
        take_url = reverse("quizzes:quiz_take", args=[quiz.pk])
        self.assertEqual(self.client.get(take_url).status_code, 200)
        data = {f"q_{q.id}": q.correct_choice_index for q in quiz.questions.all()}
        r = self.client.post(take_url, data)
        result = self.client.get(r.url)
        self.assertContains(result, "3/3")
        self.assertContains(result, "Because.")

    @patch("quizzes.views.QuizGenerator")
    def test_regenerate_replaces_active_and_keeps_attempts(self, gen_cls):
        gen_cls.return_value.generate.return_value = make_payload(1)
        gen_cls.return_value.model_used = "fake"
        url = reverse("documents:document_generate_quiz", args=[self.doc.pk])
        self.client.post(url)
        first = Quiz.objects.get()
        self.client.post(reverse("quizzes:quiz_take", args=[first.pk]),
                         {f"q_{first.questions.first().id}": 0})
        self.client.post(url)
        self.assertEqual(Quiz.objects.filter(is_active=True).count(), 1)
        self.assertEqual(QuizAttempt.objects.filter(quiz=first).count(), 1)

    @patch("quizzes.views.QuizGenerator")
    def test_failed_generation_creates_nothing(self, gen_cls):
        gen_cls.return_value.generate.side_effect = QuizGenerationError("x")
        self.client.post(reverse("documents:document_generate_quiz", args=[self.doc.pk]))
        self.assertEqual(Quiz.objects.count(), 0)
