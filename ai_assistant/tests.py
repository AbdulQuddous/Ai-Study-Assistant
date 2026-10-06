from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from ai_assistant.services.rag import RAGService
from documents.models import Document, DocumentChunk, Subject


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

        # Real DocumentChunk fixture — used by 29.19/29.20 tests that
        # need an actual model instance (not the FakeChunk stub).
        self.chunk = DocumentChunk.objects.create(
            document=self.document,
            chunk_index=0,
            content="Django is a Python web framework.",
            embedding=[1.0, 0.0],
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
    # Validation — explicit arguments
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

    # ------------------------------------------------------------------
    # 29.19 — Minimum confidence gate
    # ------------------------------------------------------------------

    @override_settings(RAG_MIN_CONFIDENCE=0.80)
    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_rag_rejects_low_confidence_results(
        self, mock_llm, mock_retrieve
    ):
        # Best score 0.65 < 0.80 → reject
        mock_retrieve.return_value = [
            {
                "chunk": type(
                    "FakeChunk",
                    (),
                    {"id": 1, "chunk_index": 0, "content": "x"},
                )(),
                "score": 0.65,
            },
        ]

        result = RAGService().answer(
            document=self.document,
            question="Something unrelated",
        )

        self.assertIn("sufficiently relevant", result["answer"])
        self.assertEqual(result["sources"], [])
        mock_llm.assert_not_called()

    @override_settings(RAG_MIN_CONFIDENCE=0.80)
    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_rag_accepts_high_confidence_results(
        self, mock_llm, mock_retrieve
    ):
        mock_retrieve.return_value = [
            {
                "chunk": type(
                    "FakeChunk",
                    (),
                    {"id": 1, "chunk_index": 0, "content": "x"},
                )(),
                "score": 0.90,
            },
        ]
        mock_llm.return_value = "Django is a web framework."

        result = RAGService().answer(
            document=self.document,
            question="What is Django?",
        )

        self.assertEqual(
            result["answer"], "Django is a web framework."
        )
        self.assertEqual(len(result["sources"]), 1)
        mock_llm.assert_called_once()

    @override_settings(RAG_MIN_CONFIDENCE=0.35)
    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_min_confidence_boundary_at_threshold(
        self, mock_llm, mock_retrieve
    ):
        # Score exactly equal to min_confidence → accept (>=, not >)
        mock_retrieve.return_value = [
            {
                "chunk": type(
                    "FakeChunk",
                    (),
                    {"id": 1, "chunk_index": 0, "content": "x"},
                )(),
                "score": 0.35,
            },
        ]
        mock_llm.return_value = "answer"

        RAGService().answer(
            document=self.document,
            question="test",
        )

        mock_llm.assert_called_once()

    def test_rejects_invalid_min_confidence(self):
        with self.assertRaises(ValueError):
            RAGService().answer(
                document=self.document,
                question="test",
                min_confidence=1.5,
            )

    # ------------------------------------------------------------------
    # 29.20 — End-to-end confidence behavior
    # ------------------------------------------------------------------

    @override_settings(RAG_MIN_CONFIDENCE=0.80)
    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_rag_rejects_irrelevant_question(
        self, mock_llm, mock_retrieve
    ):
        mock_retrieve.return_value = [
            {
                "chunk": self.chunk,
                "score": 0.42,
            },
        ]

        result = RAGService().answer(
            document=self.document,
            question="What is the capital of France?",
        )

        self.assertEqual(result["sources"], [])
        self.assertIn("sufficiently relevant", result["answer"])
        mock_llm.assert_not_called()

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_rag_handles_no_retrieved_chunks(
        self, mock_llm, mock_retrieve
    ):
        mock_retrieve.return_value = []

        result = RAGService().answer(
            document=self.document,
            question="What is Django?",
        )

        self.assertEqual(result["sources"], [])
        self.assertIn(
            "could not find relevant information",
            result["answer"],
        )
        mock_llm.assert_not_called()

    @override_settings(RAG_MIN_CONFIDENCE=0.80)
    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_rag_accepts_high_confidence_retrieval(
        self, mock_llm, mock_retrieve
    ):
        mock_retrieve.return_value = [
            {
                "chunk": self.chunk,
                "score": 0.91,
            },
        ]
        mock_llm.return_value = "Django is a Python web framework."

        result = RAGService().answer(
            document=self.document,
            question="What is Django?",
        )

        self.assertEqual(
            result["answer"],
            "Django is a Python web framework.",
        )
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(
            result["sources"][0]["chunk_index"],
            self.chunk.chunk_index,
        )
        self.assertAlmostEqual(
            result["sources"][0]["score"],
            0.91,
        )
        mock_llm.assert_called_once()

    @override_settings(RAG_MIN_CONFIDENCE=0.60)
    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_rag_returns_multiple_sources(
        self, mock_llm, mock_retrieve
    ):
        second_chunk = DocumentChunk.objects.create(
            document=self.document,
            chunk_index=1,
            content="Django uses URL patterns to route requests.",
            embedding=[0.8, 0.2],
        )

        mock_retrieve.return_value = [
            {"chunk": self.chunk, "score": 0.88},
            {"chunk": second_chunk, "score": 0.76},
        ]
        mock_llm.return_value = "Django is a Python web framework."

        result = RAGService().answer(
            document=self.document,
            question="What is Django?",
        )

        self.assertEqual(len(result["sources"]), 2)
        self.assertEqual(result["sources"][0]["chunk_index"], 0)
        self.assertEqual(result["sources"][1]["chunk_index"], 1)

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_rag_source_contains_chunk_content(
        self, mock_llm, mock_retrieve
    ):
        mock_retrieve.return_value = [
            {"chunk": self.chunk, "score": 0.90},
        ]
        mock_llm.return_value = "Test answer"

        result = RAGService().answer(
            document=self.document,
            question="What is Django?",
        )

        source = result["sources"][0]
        self.assertEqual(source["content"], self.chunk.content)

    @override_settings(RAG_MIN_CONFIDENCE=0.60)
    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService.generate")
    def test_rag_multiple_chunks_with_low_best_score_rejected(
        self, mock_llm, mock_retrieve
    ):
        """Multiple low-scoring chunks: even with several results,
        the best score gates the answer."""
        second = DocumentChunk.objects.create(
            document=self.document,
            chunk_index=1,
            content="Other content",
            embedding=[0.5, 0.5],
        )

        mock_retrieve.return_value = [
            {"chunk": self.chunk, "score": 0.55},
            {"chunk": second, "score": 0.40},
        ]

        result = RAGService().answer(
            document=self.document,
            question="What is the capital of France?",
        )

        self.assertEqual(result["sources"], [])
        self.assertIn("sufficiently relevant", result["answer"])
        mock_llm.assert_not_called()