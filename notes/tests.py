from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from subjects.models import Subject
from .models import Note


class NoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner")
        cls.other = User.objects.create_user("other")
        cls.subject = Subject.objects.create(user=cls.owner, name="Biology")
        cls.foreign_subject = Subject.objects.create(user=cls.other, name="Private subject")
        cls.note = Note.objects.create(user=cls.owner, subject=cls.subject, title="Cells", content="Mitochondria")
        cls.private = Note.objects.create(user=cls.other, subject=cls.foreign_subject, title="Private note", content="Mitochondria")

    def setUp(self):
        self.client.force_login(self.owner)

    def test_crud_renders_and_redirects(self):
        data = {"subject": self.subject.pk, "title": "New note", "content": "Text"}
        self.assertEqual(self.client.get(reverse("notes:note_create")).status_code, 200)
        self.assertRedirects(self.client.post(reverse("notes:note_create"), data), reverse("notes:note_list"))
        note = Note.objects.get(title="New note")
        self.assertEqual(note.user, self.owner)
        self.assertEqual(self.client.get(reverse("notes:note_detail", args=[note.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("notes:note_update", args=[note.pk])).status_code, 200)
        data["title"] = "Updated note"
        self.assertRedirects(self.client.post(reverse("notes:note_update", args=[note.pk]), data), reverse("notes:note_detail", args=[note.pk]))
        self.assertEqual(self.client.get(reverse("notes:note_delete", args=[note.pk])).status_code, 200)
        self.assertRedirects(self.client.post(reverse("notes:note_delete", args=[note.pk])), reverse("notes:note_list"))
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())

    def test_search_title_content_subject_and_ownership(self):
        for query in ["  Cells  ", "Mitochondria", "Biology"]:
            response = self.client.get(reverse("notes:note_list"), {"q": query})
            self.assertEqual(list(response.context["page_obj"]), [self.note])
            self.assertNotContains(response, "Private note")

    def test_search_pagination_preserves_query(self):
        Note.objects.bulk_create([Note(user=self.owner, subject=self.subject,
            title=f"Cells {i}", content="Text") for i in range(8)])
        response = self.client.get(reverse("notes:note_list"), {"q": "Cells", "page": "2"})
        self.assertEqual(len(response.context["page_obj"]), 3)
        self.assertContains(response, "q=Cells")
        self.assertEqual(response.context["page_obj"].paginator.count, 9)

    def test_empty_search_and_empty_library_states(self):
        self.assertContains(self.client.get(reverse("notes:note_list"), {"q": "missing"}), "No notes found")
        Note.objects.filter(user=self.owner).delete()
        self.assertContains(self.client.get(reverse("notes:note_list")), "don't have any notes", html=False)

    def test_foreign_note_and_subject_rejected(self):
        for action in ["detail", "update", "delete"]:
            url = reverse(f"notes:note_{action}", args=[self.private.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {}).status_code, 404)
        response = self.client.post(reverse("notes:note_create"), {
            "subject": self.foreign_subject.pk, "title": "Invalid", "content": "Text",
        })
        self.assertIn("subject", response.context["form"].errors)
        self.assertFalse(Note.objects.filter(title="Invalid").exists())

    def test_content_is_escaped(self):
        self.note.content = "<script>alert(1)</script>"
        self.note.save()
        response = self.client.get(reverse("notes:note_detail", args=[self.note.pk]))
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_anonymous_views_require_login(self):
        self.client.logout()
        for action in ["list", "create", "detail", "update", "delete"]:
            args = [] if action in {"list", "create"} else [self.note.pk]
            self.assertEqual(self.client.get(reverse(f"notes:note_{action}", args=args)).status_code, 302)
