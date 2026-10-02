from .llm import LLMService
from .retriever import DocumentRetriever
from ..prompts.rag import build_rag_prompt


class RAGService:
    def __init__(self):
        self.llm = LLMService()
        self.retriever = DocumentRetriever()

    def answer(
        self,
        document,
        question,
        top_k=5,
    ):
        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        if not document.extracted_text.strip():
            raise ValueError(
                "Document does not contain extractable text."
            )

        retrieved_chunks = self.retriever.retrieve(
            document=document,
            query=question,
            top_k=top_k,
        )

        if not retrieved_chunks:
            return (
                "I could not find relevant information "
                "in the provided study material."
            )

        prompt = build_rag_prompt(
            question=question,
            retrieved_chunks=retrieved_chunks,
        )

        answer = self.llm.generate(prompt)

        return answer