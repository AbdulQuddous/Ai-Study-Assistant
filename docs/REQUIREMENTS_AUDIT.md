# Requirements audit — 2026-10-28

Inspected the existing models, migrations, forms, services, views, URL configurations,
templates, admin registrations, dependency environment and tests before modifying code.
Branch: `main`. Pre-existing edits: `quizzes/api_urls.py`, `api_views.py`,
`serializers.py`, `tests.py`; retain these edits. No commits were authorized during the
initial audit; the user later explicitly requested separate commits.

Status below records the **initial audit**, before remediation. P0 means security or
data consistency; P1 means core correctness; P2 means portfolio readiness; P3 is optional.
Tests named in the action column are planned regression coverage where baseline coverage
was absent. The implementation report records final outcomes.

| Category / requirement | Status | Implementation / relevant files | Existing tests | Defect or gap / recommended action | Priority | Acceptance criteria |
| --- | --- | --- | --- | --- | --- | --- |
| A Authentication | DEFECT FOUND | `accounts/forms.py`, `views.py`, `urls.py` | Empty test module | Registration hashes passwords but bypasses configured password validators; add validation and auth/CSRF tests | P0 | Weak passwords rejected; valid signup/login/logout and protected profile work |
| A Subject CRUD | DEFECT FOUND | `subjects/models.py`, `forms.py`, `views.py`, `urls.py`, `templates/subjects/` | Empty | Owner filters exist; successful mutations reverse unnamespaced URLs; fix redirects | P1 | Owner CRUD renders and redirects; other users get 404 |
| A Notes CRUD and search | DEFECT FOUND | `notes/`, `templates/notes/` | Empty | Owner filters, subject filtering and six-item pagination exist; broken template/redirect URL names; empty search results render blank | P1 | CRUD, title/content/subject search, pagination and empty states work without cross-user data |
| A Document records | DEFECT FOUND | `documents/views.py`, `forms.py`, `models.py` | Empty | Owner filters present; upload redirect broken; extraction and embedding failures escape view | P1 | Valid upload persists fully; failures show useful form errors |
| B PDF validation | PARTIALLY COMPLETE | `documents/validators.py`, `services/pdf_extractor.py` | None | Extension and 10 MB limit exist; no signature, encrypted/malformed/empty handling | P0 | Reject invalid content, encrypted and textless files without 500 or partial records |
| B Processing and reprocessing | DEFECT FOUND | `documents/services/processor.py`, `chunker.py`, `text_cleaner.py` | None | Atomic transaction exists, but deletes old chunks before generating replacements; zip silently truncates mismatched embedding batches; actual chunks are 500/100 | P0 | Validate replacements before atomic write; failure retains old text/chunks; no duplicate or incomplete batches |
| A Embeddings | PARTIALLY COMPLETE | `ai_assistant/services/embeddings.py`, `chunk_embeddings.py` | Indirect real model initialization | Model cached but eagerly initialized; batch count unchecked | P1 | Lazy model loading; validated finite, consistent vectors; batch failure retains stored vectors |
| B Gemini integration | DEFECT FOUND | `ai_assistant/services/llm.py` | No direct tests | Uses exceptions from a different SDK, logs raw errors, accepts empty responses | P1 | Correct SDK error handling, bounded retries, no raw provider payload logging, nonempty output |
| A Summaries | DEFECT FOUND | `summarizer.py`, document summary view | None | Persistence exists; constructor outside error handler; missing API key causes 500 | P1 | Missing configuration/provider/empty response shows error and retains old summary |
| A Semantic retrieval | DEFECT FOUND | `retriever.py`, `similarity.py` | RAG mocks only | Fallback returns chunks below configured threshold | P1 | Ranking/top-k honor threshold; no embeddings avoids model initialization; dimension errors handled by UI |
| A RAG and sources | PARTIALLY COMPLETE | `rag.py`, `prompts/rag.py` | 24 config/confidence tests | Best-score confidence, context-only prompt and exact source snapshots exist; eager initialization and empty output gaps | P1 | No context/low score makes no LLM call; sources match retrieved chunks; errors safe |
| A Chat persistence | DEFECT FOUND | `ai_assistant/views.py`, `models.py`, Q&A template | None | Owner-scoped history exists; constructor outside try; prints raw exceptions | P1 | Initialization/provider failure shows generic error and creates no chat; valid source snapshots persist |
| A Quiz core | COMPLETE | `quizzes/models.py`, services, views, templates | 37 generation/persistence/scoring/view/integration tests | Existing transactions, server scoring and access checks; preserve design | P1 | Existing suite passes; targeted fixes only for confirmed gaps below |
| B Quiz generation errors | DEFECT FOUND | `quizzes/views.py`, `services/quiz_generator.py` | Mocked generation errors | Missing Gemini key raises ValueError before QuizError handler; final error includes raw generated material | P1 | Initialization failure handled; logs/errors omit provider payload and raw study content |
| B Quiz invalid difficulty | DEFECT FOUND | `quizzes/services/quiz_generator.py` | String difficulty only | Final review reproduced TypeError when AI returns an array/object for difficulty; validate type before set membership | P1 | Malformed JSON values trigger controlled generation rejection/retry |
| B Quiz source references | MISSING | `quiz_generator.py`, `quiz_persister.py`, `prompts/quiz_generation.py` | None | Source field always persisted as empty; prompt carries no chunk IDs | P1 | References validated against actual selected document chunks and stored per question |
| B Quiz history navigation | DEFECT FOUND | Document detail and quiz result templates | No history link regression | Document links include inactive quizzes that 404; old results offer invalid retake links | P1 | Only active quiz action links; historical results still readable |
| C Record ownership / CSRF / escaping | PARTIALLY COMPLETE | All app views/forms; Django middleware | Quiz web tests only | Scoped queries and autoescaping present; missing systematic regression coverage | P0 | Foreign IDs and foreign subject choices denied; CSRF remains enabled |
| C PDF download privacy | DEFECT FOUND | `config/urls.py`, document templates | None | Debug media handler serves files without login/ownership | P0 | Owner-only streaming endpoint; public media route removed; deploy must keep media private |
| C Configuration | DEFECT FOUND | `config/settings.py`, `.gitignore` | None | Hardcoded Django key, unconditional DEBUG, no environment example; `.env`, SQLite and media ignored and untracked | P0 | Environment key/debug/hosts and secure production mode; safe example; no secrets included |
| D Dashboard | PARTIALLY COMPLETE | `dashboard/views.py`, `urls.py`, template; root URLs | Empty | Links-only page; duplicate root placeholder; login redirect points to unwired `/dashboard/` | P1 | Both routes resolve to real owner-scoped counts, recent resources/results and useful empty states |
| D Navigation / styling | PARTIALLY COMPLETE | `templates/base.html` | None | Notes absent from navigation; Bootstrap classes without stylesheet; inconsistent message display | P2 | Existing template design usable on mobile, notes reachable, messages and labels visible |
| E Critical test coverage | PARTIALLY COMPLETE | `*/tests.py` | 61 total discovered | Only RAG config and Quiz core tests; RAG tests initialize actual model/network | P1 | Deterministic mocked AI tests; auth/CRUD/upload/reprocessing/retrieval/dashboard/API coverage |
| A Existing API | PARTIALLY COMPLETE | Mounted `quizzes/api_urls.py`, serializers, views; `api/` empty placeholder | None | Existing list/detail and in-progress submit endpoint; no pagination; explanations reveal answer hints before attempt | P1 | Preserve existing endpoints; scoped authenticated, paginated, answer hints excluded; submission tests |
| B Migrations | COMPLETE | Existing migration chain | Baseline system checks | All installed; no schema changes detected | P1 | Final dry-run/check pass; no migrations/data deleted or applied |
| F Setup / dependencies | DEFECT FOUND | `requirements.txt`, installed venv | `pip check` passes installed env | Imports langchain-text-splitters and google-api-core missing from manifest | P2 | Declare existing splitter dependency; use genai exceptions removing extra google-api-core import; no major upgrades |
| F Documentation / deployment | MISSING | No README, env example, deployment config or screenshots | None | Document actual architecture, workflows/setup/security/limits; no deployment claims | P2 | Reproducible documented commands; screenshots captured or explicitly outstanding |
| G Analytics | OPTIONAL ENHANCEMENT | Quiz attempts contain scores/totals/time | None | Existing scope does not require a dedicated analytics page; defer | P3 | If added later, percentages distinguish attempts and question totals |
| G Global search | OPTIONAL ENHANCEMENT | Notes already implement search | None | Cross-module search is not required; defer | P3 | Existing notes search verified without private data exposure |
| G Background jobs / external DB / expanded API | OPTIONAL ENHANCEMENT | Synchronous services, SQLite, current Quiz API | None | No evidence requiring new infrastructure; defer | P3 | Evaluate separately with measured workload |

## Implementation plan

1. Fix URL integration, authentication validation, private downloads and configuration.
2. Make PDF validation and replacement processing atomic and failure-safe; validate batches.
3. Correct SDK retry/error behavior and retrieval filtering; test RAG/chat failure paths.
4. Repair verified Quiz initialization, source and history defects; retain existing API edits.
5. Complete dashboard and incremental navigation/empty-state fixes.
6. Add critical regression tests, run full checks, document actual implementation and limits.

## Initial verification

- Python 3.12.3; installed Django 6.1.1, DRF 3.18.0, google-genai 2.22.0,
  sentence-transformers 6.1.0, pypdf 6.16.2, python-dotenv 1.2.3.
- `manage.py check`: no issues. `showmigrations`: all existing migrations applied.
- `makemigrations --check --dry-run`: no changes. `migrate --check`: exit 0.
- `pip check`: no broken installed requirements.
- Plain baseline `manage.py test` discovered 61 tests but was interrupted after
  Hugging Face DNS retry stalls. Rerun with cached-model offline flags to establish result.
- Live Gemini and fresh package/model downloads are not verified by unit tests.

## Remediation outcome

All identified required code defects above have targeted fixes and regression coverage;
see [the implementation report](IMPLEMENTATION_REPORT.md) for final observed checks.
No model or migration changes were needed. Optional analytics, global search and new
infrastructure were deferred. Browser screenshots were completed during the subsequent authorized UI work; see
[UI_REVIEW.md](UI_REVIEW.md). Fresh dependency installation and live Gemini model/account
validation remain unverified environmental/manual release checks.

Production-mode checking additionally identified Django's rejection of the development
console email backend (`mail.E001`). Settings now select environment-configured SMTP
when debug is disabled; no email feature or delivery verification is claimed. HSTS remains
an explicit deployment decision and still produces `security.W004` when unset.
