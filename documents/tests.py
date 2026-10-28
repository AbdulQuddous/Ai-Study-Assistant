import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from subjects.models import Subject
from .models import Document, DocumentChunk
from .services.chunker import chunk_text
from .services.pdf_extractor import extract_text_from_pdf
from .services.processor import process_document
from .services.text_cleaner import clean_text
from .validators import validate_pdf


def pdf_bytes(text="Django is a Python web framework.", encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    if text:
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("private-password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class PDFUtilityTests(SimpleTestCase):
    def test_extension_size_and_signature_validation(self):
        for name, data in [("file.txt", b"%PDF-"), ("file.pdf", b"not a PDF"),
                           ("large.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024))]:
            with self.subTest(name=name), self.assertRaises(ValidationError):
                validate_pdf(SimpleUploadedFile(name, data))
        upload = SimpleUploadedFile("valid.PDF", pdf_bytes())
        upload.seek(3)
        validate_pdf(upload)
        self.assertEqual(upload.tell(), 3)

    def test_extracts_real_pdf_text(self):
        self.assertIn("Django", extract_text_from_pdf(io.BytesIO(pdf_bytes())))

    def test_empty_encrypted_and_malformed_pdf(self):
        for data in [pdf_bytes(text=""), pdf_bytes(encrypted=True), b"%PDF-1.7\nbroken"]:
            with self.subTest(data_size=len(data)), self.assertRaises(Exception):
                extract_text_from_pdf(io.BytesIO(data))

    def test_text_cleaning(self):
        self.assertEqual(clean_text("  A\r\n\r\n\r\nB\t  C  "), "A\n\nB C")
        self.assertEqual(clean_text(None), "")

    def test_chunk_size_overlap_and_validation(self):
        pieces = chunk_text("x" * 1200, chunk_size=500, overlap=100)
        self.assertEqual([len(p) for p in pieces], [500, 500, 400])
        self.assertEqual(chunk_text(""), [])
        for size, overlap in [(0, 0), (100, -1), (100, 100)]:
            with self.assertRaises(ValueError):
                chunk_text("Text", chunk_size=size, overlap=overlap)


class DocumentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner")
        cls.other = User.objects.create_user("other")
        cls.subject = Subject.objects.create(user=cls.owner, name="Biology")
        cls.foreign_subject = Subject.objects.create(user=cls.other, name="Private subject")
        cls.document = Document.objects.create(user=cls.owner, subject=cls.subject,
            title="Study PDF", extracted_text="Original text", ai_summary="Saved summary")
        cls.private = Document.objects.create(user=cls.other, subject=cls.foreign_subject, title="Private PDF")
        cls.chunk = DocumentChunk.objects.create(document=cls.document, chunk_index=0,
            content="Original text", embedding=[1.0, 0.0])

    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.media = override_settings(MEDIA_ROOT=self.storage.name)
        self.media.enable()
        self.addCleanup(self.media.disable)
        self.client.force_login(self.owner)

    def upload(self, data=None, name="study.pdf", subject=None):
        return self.client.post(reverse("documents:document_upload"), {
            "title": "New PDF", "subject": subject or self.subject.pk,
            "file": SimpleUploadedFile(name, data if data is not None else pdf_bytes()),
        })

    @patch("documents.services.processor.EmbeddingService")
    def test_valid_upload_is_fully_processed(self, embedding):
        embedding.return_value.embed_texts.side_effect = lambda texts: [[1.0, 0.0] for _ in texts]
        response = self.upload()
        self.assertRedirects(response, reverse("documents:document_list"))
        document = Document.objects.get(title="New PDF")
        self.assertEqual(document.user, self.owner)
        self.assertIn("Django", document.extracted_text)
        self.assertEqual(document.chunks.count(), 1)
        self.assertEqual(document.chunks.get().embedding, [1.0, 0.0])
        self.assertTrue(Path(document.file.path).exists())

    def test_invalid_uploads_create_no_records(self):
        cases = [("study.txt", b"%PDF-"), ("study.pdf", b"fake"),
                 ("study.pdf", b"%PDF-1.7\nbroken"), ("study.pdf", pdf_bytes(text="")),
                 ("study.pdf", pdf_bytes(encrypted=True)),
                 ("study.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024))]
        for name, data in cases:
            with self.subTest(name=name, size=len(data)):
                response = self.upload(data, name)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertFalse(Document.objects.filter(title="New PDF").exists())
        self.assertEqual(list(Path(self.storage.name).rglob("*.pdf")), [])

    @patch("documents.services.processor.EmbeddingService")
    def test_embedding_failure_does_not_persist_upload(self, embedding):
        embedding.return_value.embed_texts.side_effect = RuntimeError("private provider details")
        response = self.upload()
        self.assertContains(response, "Unable to process this PDF")
        self.assertNotContains(response, "private provider details")
        self.assertFalse(Document.objects.filter(title="New PDF").exists())
        self.assertEqual(list(Path(self.storage.name).rglob("*.pdf")), [])

    @patch("documents.services.processor.EmbeddingService")
    def test_bad_embedding_batches_preserve_existing_state(self, embedding):
        for vectors in [[], [[1, float("nan")]], [[True, 0]], [[]], [[1, 0], [0, 1]]]:
            embedding.return_value.embed_texts.return_value = vectors
            self.document.extracted_text = "Replacement text"
            with self.subTest(vectors=vectors), self.assertRaises(ValueError):
                process_document(self.document)
            self.document.refresh_from_db()
            self.assertEqual(self.document.extracted_text, "Original text")
            self.assertTrue(DocumentChunk.objects.filter(pk=self.chunk.pk).exists())

    @patch("documents.services.processor.EmbeddingService")
    def test_database_failure_rolls_back_replacement(self, embedding):
        embedding.return_value.embed_texts.return_value = [[1, 0]]
        self.document.extracted_text = "Replacement text"
        with patch("documents.services.processor.DocumentChunk.objects.bulk_create", side_effect=DatabaseError("failure")):
            with self.assertRaises(DatabaseError):
                process_document(self.document)
        self.document.refresh_from_db()
        self.assertEqual(self.document.extracted_text, "Original text")
        self.assertTrue(DocumentChunk.objects.filter(pk=self.chunk.pk).exists())

    @patch("documents.services.processor.EmbeddingService")
    def test_reprocessing_replaces_without_duplicates(self, embedding):
        embedding.return_value.embed_texts.return_value = [[0, 1]]
        self.document.extracted_text = "  Replacement\ttext "
        process_document(self.document)
        process_document(self.document)
        self.document.refresh_from_db()
        self.assertEqual(self.document.extracted_text, "Replacement text")
        self.assertEqual(list(self.document.chunks.values_list("content", "embedding")), [("Replacement text", [0, 1])])

    @patch("documents.services.processor.EmbeddingService")
    def test_empty_reprocessing_preserves_existing_chunks_without_loading_model(self, embedding):
        self.document.extracted_text = "  "
        with self.assertRaises(ValueError):
            process_document(self.document)
        embedding.assert_not_called()
        self.assertTrue(DocumentChunk.objects.filter(pk=self.chunk.pk).exists())

    def test_private_file_endpoint_and_no_public_media(self):
        self.document.file.save("study.pdf", SimpleUploadedFile("study.pdf", pdf_bytes()))
        file_url = reverse("documents:document_file", args=[self.document.pk])
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF-"))
        response.close()
        self.assertEqual(self.client.get(self.document.file.url).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(file_url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(file_url).status_code, 302)

    def test_missing_file_returns_404(self):
        self.assertEqual(self.client.get(reverse("documents:document_file", args=[self.document.pk])).status_code, 404)

    def test_ownership_and_subject_injection(self):
        for action in ["detail", "delete", "summarize", "file"]:
            url = reverse(f"documents:document_{action}", args=[self.private.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url).status_code, 404)
        response = self.upload(subject=self.foreign_subject.pk)
        self.assertIn("subject", response.context["form"].errors)
        self.assertFalse(Document.objects.filter(title="New PDF").exists())
        response = self.client.get(reverse("documents:document_list"))
        self.assertNotContains(response, "Private PDF")

    def test_anonymous_document_pages_require_login(self):
        self.client.logout()
        for action in ["list", "upload", "detail", "delete", "summarize", "file"]:
            args = [] if action in {"list", "upload"} else [self.document.pk]
            self.assertEqual(self.client.get(reverse(f"documents:document_{action}", args=args)).status_code, 302)

    @override_settings(GEMINI_API_KEY="")
    def test_missing_summary_key_is_handled(self):
        response = self.client.post(reverse("documents:document_summarize", args=[self.document.pk]))
        self.assertContains(response, "Unable to generate the summary")
        self.document.refresh_from_db()
        self.assertEqual(self.document.ai_summary, "Saved summary")

    @patch("documents.views.Summarizer")
    def test_summary_success_and_empty_response_preserves_old(self, summarizer):
        url = reverse("documents:document_summarize", args=[self.document.pk])
        summarizer.return_value.summarize.return_value = "New summary"
        self.assertRedirects(self.client.post(url), reverse("documents:document_detail", args=[self.document.pk]))
        for result in ["", None, "   "]:
            summarizer.return_value.summarize.return_value = result
            self.assertContains(self.client.post(url), "Unable to generate the summary")
            self.document.refresh_from_db()
            self.assertEqual(self.document.ai_summary, "New summary")
