RETRY_REMINDER = (
    "\n\nIMPORTANT: Your previous response did not match the required format. "
    "Return only the JSON object, no prose, no markdown."
)


def build_quiz_prompt(context, num_questions):
    """Build the quiz-generation prompt for the given material."""
    return f"""You are an expert educator creating a multiple-choice quiz.

The quiz will test a student's understanding of the material below.

MATERIAL:
{context}

INSTRUCTIONS:
1. Generate up to {num_questions} multiple-choice questions. Fewer is acceptable if the material does not support more.
2. Each question must have exactly 4 answer choices.
3. Exactly one choice must be correct.
4. Distractors must be plausible but clearly wrong to someone who understands the material.
5. Do NOT use "All of the above" or "None of the above".
6. For each question, write a short explanation of why the correct answer is correct.
7. Assign each question a difficulty: "easy", "medium", or "hard".
8. Generate at least 1 question. Never return an empty questions list.

OUTPUT FORMAT — return ONLY valid JSON, no prose, no markdown fences:

{{
  "title": "Short descriptive title",
  "description": "One sentence about what the quiz covers.",
  "questions": [
    {{
      "text": "Question text?",
      "explanation": "Why the correct answer is correct.",
      "difficulty": "easy",
      "choices": ["A", "B", "C", "D"],
      "correct_choice_index": 0
    }}
  ]
}}
"""
