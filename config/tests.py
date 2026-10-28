import json
import os
from pathlib import Path
import secrets
import subprocess

from django.test import SimpleTestCase


class EnvironmentSettingsTests(SimpleTestCase):
    def run_settings(self, code, **overrides):
        # Explicit exported values take precedence over the local .env.
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", DJANGO_DEBUG="false",
                   DJANGO_SECRET_KEY="", DJANGO_EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
        env.update(overrides)
        return subprocess.run(
            [str(Path(os.sys.executable)), "-c", code], env=env,
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, check=False,
        )

    def test_production_requires_secret_key(self):
        result = self.run_settings("import config.settings")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY is required", result.stderr)

    def test_production_uses_secure_cookies_https_and_smtp(self):
        result = self.run_settings(
            "import config.settings as s; import json; "
            "print(json.dumps([s.DEBUG, s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, "
            "s.SECURE_SSL_REDIRECT, s.ALLOWED_HOSTS, s.MAILERS['default']['BACKEND'], "
            "s.MAILERS['default']['OPTIONS']['host']]))",
            DJANGO_SECRET_KEY=secrets.token_urlsafe(64),
            DJANGO_ALLOWED_HOSTS=" example.invalid,localhost ", DJANGO_EMAIL_HOST="smtp.example.invalid",
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), [False, True, True, True,
            ["example.invalid", "localhost"], "django.core.mail.backends.smtp.EmailBackend", "smtp.example.invalid"])

    def test_development_can_start_with_ephemeral_key(self):
        result = self.run_settings(
            "import config.settings as s; import json; "
            "print(json.dumps([s.DEBUG, bool(s.SECRET_KEY), s.SESSION_COOKIE_SECURE]))",
            DJANGO_DEBUG="true",
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), [True, True, False])
