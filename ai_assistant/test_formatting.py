from copy import deepcopy
from html import unescape
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.template.backends.django import DjangoTemplates, get_installed_libraries
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils.safestring import mark_safe

from documents.models import Document
from subjects.models import Subject

from .models import ChatMessage
from .templatetags.study_formatting import study_markdown


FUNCTION_ANSWER = """A **function** is a reusable block of code.&#x20;

Here are the key details:

* **Definition:** Use the `def` keyword.
* **Inputs:** Functions can take parameters.
* **Result:** Use the `return` keyword.
"""

SUMMARY = """Here is a summary of the Python study notes.

---

### 1. Functions
A **function** performs a specific task.&#x20;

* **Parameters:** Named inputs in a function definition.
* **Arguments:** The values you pass to a function.
* **Flexible inputs:** `*args` and `**kwargs`.

### 2. File handling
1. Open the file.
2. Read its contents.

   * Use a `with` statement to close it automatically.
"""


class StudyFormattingTests(SimpleTestCase):
    def test_explicit_registration_when_app_discovery_misses_new_library(self):
        # A running development server can miss a newly added templatetags package.
        libraries = get_installed_libraries()
        libraries.pop("study_formatting", None)
        params = deepcopy(settings.TEMPLATES[0])
        params.pop("BACKEND")
        params["NAME"] = "registration-regression"
        with patch("django.template.backends.django.get_installed_libraries", return_value=libraries):
            backend = DjangoTemplates(params)
        rendered = backend.from_string(
            '{% load study_formatting %}{{ answer|study_markdown }}'
        ).render({"answer": "A **function**.&#x20;"})
        self.assertEqual(rendered, "<p>A <strong>function</strong>.</p>\n")
        for name in ["documents/document_detail.html", "ai_assistant/document_qa.html"]:
            with self.subTest(template=name):
                backend.get_template(name)

    def test_answer_uses_emphasis_lists_and_inline_code(self):
        rendered = study_markdown(FUNCTION_ANSWER)
        self.assertIn("<strong>function</strong>", rendered)
        self.assertIn("<ul>", rendered)
        self.assertIn("<li><strong>Definition:</strong>", rendered)
        self.assertIn("<code>def</code>", rendered)
        self.assertNotIn("**", rendered)
        self.assertNotIn("&#x20;", rendered)

    def test_summary_uses_contained_headings_and_nested_lists(self):
        rendered = study_markdown(SUMMARY)
        self.assertIn("<h3>1. Functions</h3>", rendered)
        self.assertIn("<h3>2. File handling</h3>", rendered)
        self.assertIn("<ol>", rendered)
        self.assertIn("<ul>", rendered)
        self.assertIn("<hr", rendered)
        self.assertNotIn("###", rendered)
        self.assertNotIn("&#x20;", rendered)

    def test_entities_become_readable_text(self):
        rendered = study_markdown("A&#x20;function &amp; a&#160;parameter.")
        self.assertEqual(rendered, "<p>A function &amp; a parameter.</p>\n")
        self.assertEqual(study_markdown("A&amp;#x20;function"), "<p>A function</p>\n")

    def test_python_stars_and_method_names_are_preserved_inside_code(self):
        rendered = study_markdown("Use `*args`, `**kwargs`, `2 ** 3`, and `__init__`.")
        for code in ["*args", "**kwargs", "2 ** 3", "__init__"]:
            self.assertIn(f"<code>{code}</code>", rendered)

    def test_code_blocks_preserve_backslashes_and_markup_as_code(self):
        source = '```python\npattern = r"\\*\\*literal\\*\\*"\ndef example(**kwargs):\n    return "<script>"\n```'
        rendered = study_markdown(source)
        self.assertIn('<pre><code class="language-python">', rendered)
        self.assertIn(r'pattern = r"\*\*literal\*\*"', unescape(rendered))
        self.assertIn("def example(**kwargs):", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<script>", rendered)

    def test_raw_html_and_previously_marked_safe_input_are_escaped(self):
        attack = '<script>alert("unsafe")</script><img src=x onerror=alert(1)>'
        for source in [attack, mark_safe(attack)]:
            with self.subTest(source_type=type(source).__name__):
                rendered = study_markdown(source)
                self.assertNotIn("<script>", rendered)
                self.assertNotIn("<img", rendered)
                self.assertIn("&lt;script&gt;", rendered)

    def test_encoded_html_is_escaped_after_decoding(self):
        rendered = study_markdown("&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_images_and_links_do_not_generate_active_content(self):
        rendered = study_markdown(
            "![preview](https://example.test/track) "
            "[open](javascript:alert(1)) <https://example.test>"
        )
        self.assertNotIn("<img", rendered)
        self.assertNotIn("<a ", rendered)
        self.assertNotIn("href=", rendered)

    def test_plain_text_and_line_breaks_remain_readable(self):
        rendered = study_markdown("First line\nSecond line\n\nA new paragraph.")
        self.assertIn("First line<br", rendered)
        self.assertIn("Second line</p>", rendered)
        self.assertIn("<p>A new paragraph.</p>", rendered)

    def test_headings_do_not_replace_page_or_section_headings(self):
        rendered = study_markdown("# Topic\n\n## Detail")
        self.assertIn("<h3>Topic</h3>", rendered)
        self.assertIn("<h4>Detail</h4>", rendered)
        self.assertNotIn("<h1>", rendered)
        self.assertNotIn("<h2>", rendered)

    def test_empty_values(self):
        self.assertEqual(study_markdown(None), "")
        self.assertEqual(study_markdown(""), "")


class StoredStudyFormattingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("reader")
        cls.subject = Subject.objects.create(user=cls.user, name="Python")
        cls.document = Document.objects.create(
            user=cls.user, subject=cls.subject, title="Python notes", ai_summary=SUMMARY,
        )
        cls.message = ChatMessage.objects.create(
            user=cls.user, document=cls.document,
            question="What is a function?", answer=FUNCTION_ANSWER,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_saved_summary_formats_immediately_without_rewriting_data(self):
        response = self.client.get(reverse("documents:document_detail", args=[self.document.pk]))
        self.assertContains(response, "<h3>1. Functions</h3>", html=True)
        self.assertContains(response, "<strong>function</strong>", html=True)
        self.assertNotContains(response, "&#x20;")
        self.document.refresh_from_db()
        self.assertEqual(self.document.ai_summary, SUMMARY)

    def test_saved_answer_formats_immediately_without_rewriting_data(self):
        response = self.client.get(reverse("ai_assistant:document_qa", args=[self.document.pk]))
        self.assertContains(response, "<strong>function</strong>", html=True)
        self.assertContains(response, "<code>return</code>", html=True)
        self.assertNotContains(response, "&#x20;")
        self.message.refresh_from_db()
        self.assertEqual(self.message.answer, FUNCTION_ANSWER)

    def test_answer_and_summary_do_not_render_embedded_script(self):
        attack = "<script>window.studyFormattingPayload=true</script>"
        self.document.ai_summary = attack
        self.document.save()
        self.message.answer = attack
        self.message.save()
        for route in ["documents:document_detail", "ai_assistant:document_qa"]:
            response = self.client.get(reverse(route, args=[self.document.pk]))
            self.assertNotContains(response, attack)
            self.assertContains(response, "&lt;script&gt;window.studyFormattingPayload=true&lt;/script&gt;")
