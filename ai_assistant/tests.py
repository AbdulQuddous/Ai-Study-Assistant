from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from subjects.models import Subject
from documents.models import Document, DocumentChunk

from .services.similarity import cosine_similarity
from .services.retriever import DocumentRetriever
from .services.rag import RAGService


class CosineSimilarityTests(TestCase):

    def test_identical_vectors_have_similarity_one(self):
        vector = [1.0, 0.0, 0.0]

        result = cosine_similarity(
            vector,
            vector,
        )

        self.assertAlmostEqual(
            result,
            1.0,
        )

    def test_orthogonal_vectors_have_similarity_zero(self):
        vector_a = [1.0, 0.0, 0.0]
        vector_b = [0.0, 1.0, 0.0]

        result = cosine_similarity(
            vector_a,
            vector_b,
        )

        self.assertAlmostEqual(
            result,
            0.0,
        )

    def test_different_dimensions_raise_error(self):
        vector_a = [1.0, 0.0]
        vector_b = [1.0, 0.0, 0.0]

        with self.assertRaises(ValueError):
            cosine_similarity(
                vector_a,
                vector_b,
            )


class RetrieverTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )

        self.subject = Subject.objects.create(
            user=self.user,
            name="Django",
            description="Django study material",
        )

        self.document = Document.objects.create(
            user=self.user,
            subject=self.subject,
            title="Django Basics",
            extracted_text="Django is a Python web framework.",
        )

        DocumentChunk.objects.create(
            document=self.document,
            chunk_index=0,
            content="Django is a Python web framework.",
            embedding=[1.0, 0.0, 0.0],
        )

        DocumentChunk.objects.create(
            document=self.document,
            chunk_index=1,
            content="Django uses models and views.",
            embedding=[0.9, 0.1, 0.0],
        )

        DocumentChunk.objects.create(
            document=self.document,
            chunk_index=2,
            content="Django supports URL routing.",
            embedding=[0.0, 1.0, 0.0],
        )

    @patch(
        "ai_assistant.services.retriever."
        "EmbeddingService.embed_text"
    )
    def test_retriever_returns_top_k_chunks(
        self,
        mock_embed_text,
    ):
        mock_embed_text.return_value = [
            1.0,
            0.0,
            0.0,
        ]

        retriever = DocumentRetriever()

        results = retriever.retrieve(
            document=self.document,
            query="What is Django?",
            top_k=2,
        )

        self.assertEqual(
            len(results),
            2,
        )

        self.assertEqual(
            results[0]["chunk"].chunk_index,
            0,
        )

        self.assertEqual(
            results[1]["chunk"].chunk_index,
            1,
        )

    @patch(
        "ai_assistant.services.retriever."
        "EmbeddingService.embed_text"
    )
    def test_retriever_returns_empty_when_no_embeddings(
        self,
        mock_embed_text,
    ):
        DocumentChunk.objects.filter(
            document=self.document
        ).update(
            embedding=None
        )

        retriever = DocumentRetriever()

        results = retriever.retrieve(
            document=self.document,
            query="What is Django?",
        )

        self.assertEqual(
            results,
            []
        )

        mock_embed_text.assert_not_called()


class RAGServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="raguser",
            password="testpass123",
        )

        self.subject = Subject.objects.create(
            user=self.user,
            name="Django",
            description="Django study material",
        )

        self.document = Document.objects.create(
            user=self.user,
            subject=self.subject,
            title="Django Basics",
            extracted_text="Django is a Python web framework.",
        )

    def test_empty_question_raises_error(self):
        rag = RAGService.__new__(RAGService)

        with self.assertRaises(ValueError):
            rag.answer(
                document=self.document,
                question="",
            )

    def test_empty_document_raises_error(self):
        self.document.extracted_text = ""
        self.document.save()

        rag = RAGService.__new__(RAGService)

        with self.assertRaises(ValueError):
            rag.answer(
                document=self.document,
                question="What is Django?",
            )

    @patch(
        "ai_assistant.services.rag.LLMService.generate"
    )
    @patch(
        "ai_assistant.services.rag.DocumentRetriever.retrieve"
    )
    def test_rag_generates_answer(
        self,
        mock_retrieve,
        mock_generate,
    ):
        mock_retrieve.return_value = [
            {
                "chunk": DocumentChunk(
                    document=self.document,
                    chunk_index=0,
                    content="Django is a Python web framework.",
                ),
                "score": 0.95,
            }
        ]

        mock_generate.return_value = (
            "Django is a Python web framework."
        )

        rag = RAGService()

        answer = rag.answer(
            document=self.document,
            question="What is Django?",
        )

        self.assertEqual(
            answer,
            "Django is a Python web framework.",
        )

        mock_retrieve.assert_called_once()
        mock_generate.assert_called_once()