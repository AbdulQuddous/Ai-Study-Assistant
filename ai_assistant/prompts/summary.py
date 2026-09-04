def build_summary_prompt(text):
    return f"""
You are an AI study assistant.

Summarize the following study material
for a student.

Requirements:
- Use simple language.
- Identify the main ideas.
- Include important concepts.
- Use bullet points where helpful.
- Do not invent information.
- Keep the summary focused.

Study material:

{text}
""".strip()