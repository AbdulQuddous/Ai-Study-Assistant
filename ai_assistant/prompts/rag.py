def build_rag_prompt(question, retrieved_chunks):
    context_parts = []

    for index, item in enumerate(
        retrieved_chunks,
        start=1,
    ):
        chunk = item["chunk"]
        score = item["score"]

        context_parts.append(
            f"""
Context {index}
Relevance score: {score:.4f}

{chunk.content}
""".strip()
        )

    context = "\n\n".join(context_parts)

    return f"""
You are an AI study assistant helping a student
understand their study material.

Answer the student's question using ONLY the
provided context.

Requirements:
- Use simple and clear language.
- Give a direct answer.
- Explain concepts when necessary.
- Do not invent information.
- Do not use outside knowledge.
- If the answer cannot be found in the provided
  context, clearly say that the information is
  not available in the provided study material.
- Use bullet points when helpful.

Retrieved study context:

{context}

Student question:

{question}
""".strip()