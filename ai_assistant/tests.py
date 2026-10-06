from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from ai_assistant.services.rag import RAGService
from documents.models import Document, Subject


class RAGServiceConfigTests(TestCase):
    """
    Verify that RAGService reads top_k and similarity_threshold from
    Django settings, honors explicit overrides, and validates inputs.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="ragtestuser",
            password="testpass123",
        )

        self.subject = Subject.objects.create(
            user=self.user,
            name="Test Subject",
        )

        self.document = Document.objects.create(
            user=self.user,
            subject=self.subject,
            title="Test Doc",
            extracted_text="Python is a programming language.",
        )

    def _stub_chunks(self):
        """Return a fake retrieved_chunks list of length 5."""
        return [
            {
                "chunk": type(
                    "FakeChunk",
                    (),
                    {
                        "id": i,
                        "chunk_index": i,
                        "content": f"chunk {i} content",
                    },
                )(),
                "score": 0.5 - (i * 0.05),
            }
            for i in range(5)
        ]

    # ------------------------------------------------------------------
    # Settings defaults
    # ------------------------------------------------------------------

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_uses_settings_top_k_default(self, mock_llm, mock_retrieve):
        mock_retrieve.return_value = []
        mock_llm.return_value = "stub"

        RAGService().answer(
            document=self.document,
            question="test question",
        )

        _, kwargs = mock_retrieve.call_args
        self.assertEqual(kwargs["top_k"], 5)
        self.assertEqual(kwargs["similarity_threshold"], 0.25)

    @override_settings(RAG_TOP_K=8, RAG_SIMILARITY_THRESHOLD=0.4)
    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_reads_settings_at_call_time(self, mock_llm, mock_retrieve):
        mock_retrieve.return_value = []
        mock_llm.return_value = "stub"

        RAGService().answer(
            document=self.document,
            question="test question",
        )

        _, kwargs = mock_retrieve.call_args
        self.assertEqual(kwargs["top_k"], 8)
        self.assertEqual(kwargs["similarity_threshold"], 0.4)

    # ------------------------------------------------------------------
    # Explicit overrides
    # ------------------------------------------------------------------

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_explicit_top_k_overrides_settings(self, mock_llm, mock_retrieve):
        mock_retrieve.return_value = []
        mock_llm.return_value = "stub"

        RAGService().answer(
            document=self.document,
            question="test question",
            top_k=2,
        )

        _, kwargs = mock_retrieve.call_args
        self.assertEqual(kwargs["top_k"], 2)

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_explicit_threshold_overrides_settings(self, mock_llm, mock_retrieve):
        mock_retrieve.return_value = []
        mock_llm.return_value = "stub"

        RAGService().answer(
            document=self.document,
            question="test question",
            similarity_threshold=0.7,
        )

        _, kwargs = mock_retrieve.call_args
        self.assertEqual(kwargs["similarity_threshold"], 0.7)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_rejects_top_k_zero(self):
        with self.assertRaises(ValueError):
            RAGService().answer(
                document=self.document,
                question="test question",
                top_k=0,
            )

    def test_rejects_top_k_negative(self):
        with self.assertRaises(ValueError):
            RAGService().answer(
                document=self.document,
                question="test question",
                top_k=-1,
            )

    def test_rejects_threshold_above_one(self):
        with self.assertRaises(ValueError):
            RAGService().answer(
                document=self.document,
                question="test question",
                similarity_threshold=1.5,
            )

    def test_rejects_threshold_below_zero(self):
        with self.assertRaises(ValueError):
            RAGService().answer(
                document=self.document,
                question="test question",
                similarity_threshold=-0.1,
            )

    def test_rejects_empty_question(self):
        with self.assertRaises(ValueError):
            RAGService().answer(
                document=self.document,
                question="",
            )

    def test_rejects_whitespace_question(self):
        with self.assertRaises(ValueError):
            RAGService().answer(
                document=self.document,
                question="   ",
            )

    def test_rejects_empty_document_text(self):
        empty_doc = Document.objects.create(
            user=self.user,
            subject=self.subject,
            title="Empty",
            extracted_text="",
        )
        with self.assertRaises(ValueError):
            RAGService().answer(
                document=empty_doc,
                question="test question",
            )

    # ------------------------------------------------------------------
    # No-result path
    # ------------------------------------------------------------------

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    def test_returns_not_found_when_no_chunks(self, mock_retrieve):
        mock_retrieve.return_value = []

        result = RAGService().answer(
            document=self.document,
            question="test question",
        )

        self.assertIn("could not find", result["answer"].lower())
        self.assertEqual(result["sources"], [])

    # ------------------------------------------------------------------
    # Successful path returns sources
    # ------------------------------------------------------------------

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_returns_sources_with_content(self, mock_llm, mock_retrieve):
        mock_retrieve.return_value = self._stub_chunks()
        mock_llm.return_value = "A for loop iterates over a sequence."

        result = RAGService().answer(
            document=self.document,
            question="What is a for loop?",
        )

        self.assertEqual(
            result["answer"],
            "A for loop iterates over a sequence.",
        )
        self.assertEqual(len(result["sources"]), 5)

        first = result["sources"][0]
        self.assertIn("chunk_id", first)
        self.assertIn("chunk_index", first)
        self.assertIn("score", first)
        self.assertIn("content", first)