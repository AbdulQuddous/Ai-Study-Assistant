from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from google.genai import errors

from documents.models import Document, DocumentChunk
from subjects.models import Subject
from .models import ChatMessage
from .services.chunk_embeddings import ChunkEmbeddingService
from .services.embeddings import EmbeddingService
from .services.llm import LLMService
from .services.query_preprocessor import preprocess_query
from .services.rag import RAGService
from .services.retriever import DocumentRetriever
from .services.similarity import cosine_similarity, validate_embedding_batch
from .services.summarizer import Summarizer


@override_settings(GEMINI_API_KEY="test-key", GEMINI_MODEL="test-model")
class LLMTests(SimpleTestCase):
    def setUp(self):
        self.client_patch = patch("ai_assistant.services.llm.genai.Client")
        self.sdk = self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.generate = self.sdk.return_value.models.generate_content

    def test_success(self):
        self.generate.return_value = SimpleNamespace(text="  Answer  ")
        self.assertEqual(LLMService().generate("Prompt"), "Answer")
        self.generate.assert_called_once_with(model="test-model", contents="Prompt")

    @override_settings(GEMINI_API_KEY="")
    def test_missing_key(self):
        with self.assertRaises(ValueError):
            LLMService()
        self.sdk.assert_not_called()

    def test_empty_input_and_output(self):
        for prompt in ["", "   ", None]:
            with self.assertRaises(ValueError):
                LLMService().generate(prompt)
        for output in ["", None, "  "]:
            self.generate.return_value = SimpleNamespace(text=output)
            with self.assertRaises(RuntimeError):
                LLMService().generate("Prompt")

    @patch("ai_assistant.services.llm.time.sleep")
    def test_transient_errors_retry_with_backoff(self, sleep):
        self.generate.side_effect = [errors.ClientError(429, {"message": "private"}),
                                    errors.ServerError(503, {"message": "private"}),
                                    SimpleNamespace(text="Recovered")]
        with self.assertLogs("ai_assistant.services.llm", level="WARNING") as logs:
            self.assertEqual(LLMService().generate("Prompt"), "Recovered")
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])
        self.assertNotIn("private", " ".join(logs.output))

    @patch("ai_assistant.services.llm.time.sleep")
    def test_permanent_error_is_not_retried(self, sleep):
        self.generate.side_effect = errors.ClientError(400, {"message": "private provider details"})
        with self.assertRaisesRegex(RuntimeError, "AI service request failed") as caught:
            LLMService().generate("Prompt")
        self.assertNotIn("private", str(caught.exception))
        self.assertEqual(self.generate.call_count, 1)
        sleep.assert_not_called()

    @patch("ai_assistant.services.llm.time.sleep")
    def test_retry_exhaustion_is_bounded(self, sleep):
        self.generate.side_effect = errors.ServerError(503, {"message": "unavailable"})
        with self.assertRaises(RuntimeError):
            LLMService().generate("Prompt", max_retries=3)
        self.assertEqual(self.generate.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("ai_assistant.services.summarizer.LLMService")
    def test_summary_service_builds_prompt_and_rejects_empty_material(self, llm):
        llm.return_value.generate.return_value = "Summary"
        self.assertEqual(Summarizer().summarize("Django content"), "Summary")
        self.assertIn("Django content", llm.return_value.generate.call_args.args[0])
        with self.assertRaises(ValueError):
            Summarizer().summarize("   ")


class EmbeddingUtilityTests(SimpleTestCase):
    @patch("ai_assistant.services.embeddings.get_embedding_model")
    def test_model_loading_is_deferred_until_valid_input(self, model):
        service = EmbeddingService()
        model.assert_not_called()
        self.assertEqual(service.embed_texts([]), [])
        with self.assertRaises(ValueError):
            service.embed_text(" ")
        model.assert_not_called()
        model.return_value.encode.return_value.tolist.return_value = [1.0, 0.0]
        self.assertEqual(service.embed_text("Django"), [1.0, 0.0])
        model.assert_called_once()

    def test_query_normalization(self):
        self.assertEqual(preprocess_query("  Django\n\tviews  "), "Django views")
        with self.assertRaises(ValueError):
            preprocess_query("  ")

    def test_similarity_and_dimension_validation(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 0]), 1)
        self.assertEqual(cosine_similarity([1, 0], [0, 1]), 0)
        self.assertEqual(cosine_similarity([0, 0], [1, 0]), 0)
        for left, right in [([1], [1, 0]), ([1, float("nan")], [1, 0]), (["x"], [1])]:
            with self.assertRaises(ValueError):
                cosine_similarity(left, right)
        with self.assertRaises(ValueError):
            validate_embedding_batch([[1], [1, 0]], 2)


@override_settings(GEMINI_API_KEY="test-key")
class RetrievalAndChatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner")
        cls.other = User.objects.create_user("other")
        cls.subject = Subject.objects.create(user=cls.owner, name="Django")
        cls.document = Document.objects.create(user=cls.owner, subject=cls.subject,
            title="Django notes", extracted_text="Django web framework")
        cls.chunk = DocumentChunk.objects.create(document=cls.document, chunk_index=0,
            content="Django is a web framework.", embedding=[1, 0])

    def setUp(self):
        self.client.force_login(self.owner)
        self.url = reverse("ai_assistant:document_qa", args=[self.document.pk])

    @patch("ai_assistant.services.embeddings.get_embedding_model")
    def test_no_chunks_or_embeddings_avoids_model_and_llm(self, model):
        self.chunk.embedding = None
        self.chunk.save()
        with override_settings(GEMINI_API_KEY=""):
            result = RAGService().answer(self.document, "What is Django?")
        self.assertEqual(result["sources"], [])
        self.assertIn("could not find", result["answer"])
        self.chunk.delete()
        self.assertEqual(DocumentRetriever().retrieve(self.document, "Django"), [])
        model.assert_not_called()

    @patch("ai_assistant.services.retriever.EmbeddingService.embed_text", return_value=[1, 0])
    def test_ranking_threshold_top_k_and_document_scope(self, embed):
        second = DocumentChunk.objects.create(document=self.document, chunk_index=1,
            content="Related", embedding=[0.8, 0.6])
        DocumentChunk.objects.create(document=self.document, chunk_index=2, content="Unrelated", embedding=[0, 1])
        another = Document.objects.create(user=self.other, subject=self.subject, title="Private")
        DocumentChunk.objects.create(document=another, chunk_index=0, content="Private chunk", embedding=[1, 0])
        retriever = DocumentRetriever()
        self.assertEqual([r["chunk"].pk for r in retriever.retrieve(self.document, "  Django\n views ", top_k=2, similarity_threshold=0.7)],
                         [self.chunk.pk, second.pk])
        embed.assert_called_with("Django views")
        self.assertEqual(len(retriever.retrieve(self.document, "Django", top_k=1, similarity_threshold=0)), 1)
        self.assertEqual(retriever.retrieve(self.document, "Django", similarity_threshold=1),
                         [{"chunk": self.chunk, "score": 1.0}])

    @patch("ai_assistant.services.retriever.EmbeddingService.embed_text", return_value=[0, 1])
    def test_below_threshold_is_not_returned_by_fallback(self, embed):
        self.assertEqual(DocumentRetriever().retrieve(self.document, "Other", similarity_threshold=0.8), [])

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService")
    def test_low_confidence_avoids_llm(self, llm, retrieve):
        retrieve.return_value = [{"chunk": self.chunk, "score": 0.4}]
        self.assertEqual(RAGService().answer(self.document, "Other", min_confidence=0.6)["sources"], [])
        llm.assert_not_called()

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService")
    def test_success_persists_exact_sources(self, llm, retrieve):
        retrieve.return_value = [{"chunk": self.chunk, "score": 0.9}]
        llm.return_value.generate.return_value = "Django is a web framework."
        response = self.client.post(self.url, {"question": "What is Django?"})
        self.assertEqual(response.status_code, 200)
        message = ChatMessage.objects.get()
        self.assertEqual(message.user, self.owner)
        self.assertEqual(message.document, self.document)
        self.assertEqual(message.sources, [{"chunk_id": self.chunk.pk, "chunk_index": 0,
            "score": 0.9, "content": self.chunk.content}])
        prompt = llm.return_value.generate.call_args.args[0]
        self.assertIn(self.chunk.content, prompt)
        self.assertIn("ONLY", prompt)
        self.assertContains(response, "Sources used")

    @patch("ai_assistant.views.RAGService", side_effect=ValueError("private initialization error"))
    def test_constructor_failure_is_handled(self, rag):
        response = self.client.post(self.url, {"question": "Django?"})
        self.assertContains(response, "Unable to answer")
        self.assertNotContains(response, "private initialization error")
        self.assertFalse(ChatMessage.objects.exists())

    @patch("ai_assistant.services.rag.DocumentRetriever.retrieve")
    @patch("ai_assistant.services.rag.LLMService")
    def test_empty_answer_and_provider_failure_create_no_history(self, llm, retrieve):
        retrieve.return_value = [{"chunk": self.chunk, "score": 0.9}]
        for value in [None, "", "  "]:
            llm.return_value.generate.return_value = value
            self.assertContains(self.client.post(self.url, {"question": "Django?"}), "Unable to answer")
            self.assertFalse(ChatMessage.objects.exists())
        llm.return_value.generate.side_effect = RuntimeError("private error")
        self.assertContains(self.client.post(self.url, {"question": "Django?"}), "Unable to answer")
        self.assertFalse(ChatMessage.objects.exists())

    @patch("ai_assistant.services.retriever.EmbeddingService.embed_text", side_effect=RuntimeError("failed"))
    def test_embedding_failure_has_safe_error(self, embed):
        self.assertContains(self.client.post(self.url, {"question": "Django?"}), "Unable to answer")
        self.assertFalse(ChatMessage.objects.exists())

    @patch("ai_assistant.services.retriever.EmbeddingService.embed_text", return_value=[1, 0, 0])
    def test_inconsistent_dimensions_have_safe_error(self, embed):
        self.assertContains(self.client.post(self.url, {"question": "Django?"}), "Unable to answer")
        self.assertFalse(ChatMessage.objects.exists())

    @patch("ai_assistant.views.RAGService")
    def test_invalid_question_never_initializes_service(self, rag):
        for question in ["  ", "x" * 1001]:
            self.assertContains(self.client.post(self.url, {"question": question}), "valid question")
        rag.assert_not_called()

    def test_history_and_page_ownership(self):
        ChatMessage.objects.create(user=self.other, document=self.document,
            question="Private history", answer="Private answer")
        self.assertNotContains(self.client.get(self.url), "Private history")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {"question": "Django?"}).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    @patch("ai_assistant.services.chunk_embeddings.EmbeddingService.embed_texts", return_value=[])
    def test_failed_embedding_regeneration_keeps_existing_vectors(self, embed):
        with self.assertRaises(ValueError):
            ChunkEmbeddingService().generate_for_document(self.document)
        self.chunk.refresh_from_db()
        self.assertEqual(self.chunk.embedding, [1, 0])
