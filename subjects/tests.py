from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Subject


class SubjectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner")
        cls.other = User.objects.create_user("other")
        cls.subject = Subject.objects.create(user=cls.owner, name="Biology")
        cls.private = Subject.objects.create(user=cls.other, name="Private subject")

    def setUp(self):
        self.client.force_login(self.owner)

    def test_crud_and_redirects(self):
        self.assertRedirects(self.client.post(reverse("subjects:subject_create"), {
            "name": "Physics", "description": "Motion",
        }), reverse("subjects:subject_list"))
        subject = Subject.objects.get(name="Physics")
        self.assertEqual(subject.user, self.owner)
        self.assertEqual(self.client.get(reverse("subjects:subject_detail", args=[subject.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("subjects:subject_update", args=[subject.pk])).status_code, 200)
        self.assertRedirects(self.client.post(reverse("subjects:subject_update", args=[subject.pk]), {
            "name": "Mechanics", "description": "Forces",
        }), reverse("subjects:subject_detail", args=[subject.pk]))
        self.assertEqual(self.client.get(reverse("subjects:subject_delete", args=[subject.pk])).status_code, 200)
        self.assertRedirects(self.client.post(reverse("subjects:subject_delete", args=[subject.pk])), reverse("subjects:subject_list"))
        self.assertFalse(Subject.objects.filter(pk=subject.pk).exists())

    def test_list_is_private(self):
        response = self.client.get(reverse("subjects:subject_list"))
        self.assertContains(response, "Biology")
        self.assertNotContains(response, "Private subject")

    def test_foreign_objects_are_inaccessible(self):
        for action in ["detail", "update", "delete"]:
            url = reverse(f"subjects:subject_{action}", args=[self.private.pk])
            with self.subTest(action=action):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {"name": "Hacked"}).status_code, 404)
        self.private.refresh_from_db()
        self.assertEqual(self.private.name, "Private subject")

    def test_anonymous_pages_require_login(self):
        self.client.logout()
        for action in ["list", "create", "detail", "update", "delete"]:
            args = [] if action in {"list", "create"} else [self.subject.pk]
            self.assertEqual(self.client.get(reverse(f"subjects:subject_{action}", args=args)).status_code, 302)
