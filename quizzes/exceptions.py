class QuizError(Exception):
    """Base for quiz module errors."""


class QuizGenerationError(QuizError):
    """The LLM failed to produce a valid quiz."""


class QuizPersistenceError(QuizError):
    """Saving the quiz to the DB failed."""


class QuizScoringError(QuizError):
    """Scoring an attempt failed."""
