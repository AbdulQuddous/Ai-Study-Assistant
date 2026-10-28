from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .forms import RegisterForm


class AuthenticationTests(TestCase):
    def test_registration_rejects_weak_password(self):
        form = RegisterForm(data={"username": "student", "email": "s@example.com",
                                  "password": "123", "password_confirm": "123"})
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_registration_validates_similarity_to_username(self):
        form = RegisterForm(data={"username": "distinctstudent", "password": "distinctstudent",
                                  "password_confirm": "distinctstudent"})
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_registration_mismatched_passwords(self):
        form = RegisterForm(data={"username": "student", "password": "A-good-passphrase-92!",
                                  "password_confirm": "other"})
        self.assertFalse(form.is_valid())

    def test_registration_hashes_password_and_opens_dashboard(self):
        password = "A-good-passphrase-92!"
        response = self.client.post(reverse("register"), {
            "username": "student", "email": "s@example.com",
            "password": password, "password_confirm": password,
        })
        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="student")
        self.assertTrue(user.check_password(password))
        self.assertNotEqual(user.password, password)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_login_logout_and_protected_profile(self):
        user = User.objects.create_user("student", password="A-good-passphrase-92!")
        self.assertEqual(self.client.get(reverse("profile")).status_code, 302)
        self.assertRedirects(self.client.post(reverse("login"), {
            "username": user.username, "password": "A-good-passphrase-92!",
        }), reverse("dashboard"))
        self.assertEqual(self.client.get("/dashboard/").status_code, 200)
        self.client.get(reverse("logout"))
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_csrf_protects_mutations(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("register"), {}).status_code, 403)
        self.assertEqual(client.post(reverse("login"), {}).status_code, 403)
