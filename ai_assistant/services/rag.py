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
        similarity_threshold=0.25,
    ):
        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        if not document.extracted_text.strip():
            raise ValueError(
                "Document does not contain extractable text."
            )

        retrieved_chunks = self.retriever.retrieve(
            document=document,
            query=question,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        if not retrieved_chunks:
            return {
                "answer": (
                    "I could not find relevant information "
                    "in the provided study material."
                ),
                "sources": [],
            }

        prompt = build_rag_prompt(
            question=question,
            retrieved_chunks=retrieved_chunks,
        )

        answer = self.llm.generate(prompt)

        sources = [
            {
                "chunk_id": item["chunk"].id,
                "chunk_index": item["chunk"].chunk_index,
                "score": item["score"],
                "content": item["chunk"].content,
            }
            for item in retrieved_chunks
        ]

        return {
            "answer": answer,
            "sources": sources,
        }