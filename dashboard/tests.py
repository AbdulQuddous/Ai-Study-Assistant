from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from documents.models import Document
from notes.models import Note
from quizzes.models import Quiz, QuizAttempt
from subjects.models import Subject


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner")
        cls.other = User.objects.create_user("other")
        for user in [cls.owner, cls.other]:
            subject = Subject.objects.create(user=user, name=f"{user.username} subject")
            Note.objects.create(user=user, subject=subject, title=f"{user.username} note", content="Content")
            document = Document.objects.create(user=user, subject=subject, title=f"{user.username} document")
            quiz = Quiz.objects.create(user=user, document=document, title=f"{user.username} quiz", question_count=4)
            old_quiz = Quiz.objects.create(user=user, document=document, title=f"{user.username} old quiz", question_count=2, is_active=False)
            QuizAttempt.objects.create(user=user, quiz=quiz, score=3, total_questions=4)
            QuizAttempt.objects.create(user=user, quiz=old_quiz, score=1, total_questions=2)

    def test_counts_recent_items_and_user_isolation(self):
        self.client.force_login(self.owner)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("dashboard"))
        self.assertLessEqual(len(queries), 11)
        for key, value in {"subject_count": 1, "note_count": 1, "document_count": 1,
                           "quiz_count": 1, "attempt_count": 2}.items():
            self.assertEqual(response.context[key], value)
        self.assertContains(response, "75%")
        self.assertContains(response, "50%")
        for kind in ["note", "document", "quiz", "subject"]:
            self.assertNotContains(response, f"other {kind}")
        self.assertEqual(len(response.context["recent_quizzes"]), 1)

    def test_empty_dashboard_and_both_routes(self):
        empty = User.objects.create_user("empty")
        self.client.force_login(empty)
        for url in ["/", "/dashboard/"]:
            response = self.client.get(url)
            self.assertEqual(response.context["attempt_count"], 0)
            self.assertContains(response, "No documents yet")
            self.assertContains(response, "No notes yet")
            self.assertContains(response, "No active quizzes yet")
            self.assertContains(response, "No quiz attempts yet")

    def test_recent_resources_are_limited(self):
        subject = self.owner.subjects.get()
        Document.objects.bulk_create([Document(user=self.owner, subject=subject, title=f"Extra {i}") for i in range(8)])
        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["document_count"], 9)
        self.assertEqual(len(response.context["recent_documents"]), 5)

    def test_anonymous_dashboard_requires_login(self):
        for url in ["/", "/dashboard/"]:
            self.assertEqual(self.client.get(url).status_code, 302)
