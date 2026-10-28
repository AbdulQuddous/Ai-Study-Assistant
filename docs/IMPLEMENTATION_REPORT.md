# Implementation report — 2026-10-28

## A. Project audit

The existing project already implemented authentication, owner-scoped subjects and notes,
PDF extraction/chunking/embeddings, Gemini summaries, semantic retrieval, RAG with source
snapshots and chat history, and a complete web Quiz module. The initial offline baseline
passed 61 tests. Models, relationships and migrations matched the current schema.

The dashboard was a links-only placeholder and `/dashboard/` was not mounted. Several
views/templates used unnamespaced URL names despite namespaced apps. PDF URLs bypassed
ownership through the debug media handler. Registration did not invoke password validators.
Upload and AI initialization failures could escape the views. Retrieval could return matches
below the configured threshold. Embedding batches could be silently truncated by `zip`.
Quiz source IDs were never populated. API explanations exposed answer hints before attempts.
Final review reproduced an unhandled TypeError for non-string AI-generated difficulty values.

The full initial requirements matrix, priorities and acceptance criteria are in
[REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md). Dedicated analytics, global search,
background workers, PostgreSQL and more APIs are optional; they were not added.

## B. Work completed and file inventory

| Files | Reason / resulting behavior |
| --- | --- |
| `accounts/forms.py`, `accounts/tests.py` | Invoke Django password validation with user attributes; cover signup hashing, mismatches, login/logout, profile protection and CSRF |
| `subjects/views.py`, `subjects/tests.py` | Correct namespaced redirects and verify CRUD/ownership |
| `notes/views.py`, `notes/tests.py`, `templates/notes/note_confirm_delete.html`, `note_detail.html`, `note_form.html`, `note_list.html` | Fix route names and blank empty results; preserve existing title/content/subject search and pagination; add access and escaping coverage |
| `config/urls.py` | Mount real dashboard at both `/` and `/dashboard/`; remove public media handler |
| `config/settings.py`, `config/tests.py`, `.env.example` | Repository-root dotenv loading, environment secret/debug/hosts, production startup guard, HTTPS/cookies, SMTP configuration, static paths, API pagination and default authenticated permissions |
| `documents/validators.py`, `documents/services/pdf_extractor.py` | Check PDF signature without changing stream position; reject encrypted/textless PDFs and handle malformed input through the upload form |
| `documents/services/processor.py` | Generate/validate all replacement vectors before an atomic text/chunk replacement; do not hold a database transaction during model work; reject empty/mismatched batches |
| `documents/views.py`, `documents/urls.py`, `documents/tests.py` | Handle upload/summary failures; stream PDFs after owner lookup; private/no-store cache header; cover genuine generated PDF fixtures, rollback, reprocessing and access |
| `templates/documents/document_detail.html`, `document_list.html`, `document_confirm_delete.html` | Use private downloads, list active quizzes with working action links, avoid duplicate messages, accurately describe retained stored files |
| `ai_assistant/services/embeddings.py` | Defer heavy model import and initialization until actual embedding work; retain existing cached model/provider |
| `ai_assistant/services/similarity.py`, `chunk_embeddings.py` | Validate batch counts, consistent dimensions and finite numeric vectors before persistence or similarity calculations |
| `ai_assistant/services/llm.py` | Handle google-genai APIError codes, bounded backoff, blank prompts/answers and safe error messages; remove incorrect google-api-core dependency |
| `ai_assistant/services/retriever.py`, `rag.py`, `ai_assistant/views.py`, `prompts/rag.py` | Honor configured retrieval threshold, defer LLM initialization until evidence qualifies, handle initialization/empty-answer errors and retain exact source snapshots; remove raw exception printing |
| `ai_assistant/tests.py`, `ai_assistant/test_reliability.py` | Isolate tests from local Gemini credentials and real models; add SDK/retrieval/chat/source/persistence regression coverage |
| `quizzes/services/quiz_generator.py`, `quiz_persister.py`, `quizzes/prompts/quiz_generation.py` | Label sampled chunks, validate/persist only actual document source IDs, check document ownership, reject non-string difficulty, omit raw provider output from errors/logs |
| `quizzes/views.py`, `quizzes/templates/quizzes/quiz_result.html`, `quiz_detail.html`, `quiz_take.html` | Handle missing Gemini configuration, show available source excerpts in answer review, keep old results readable without broken retake links, use shared messages |
| `quizzes/serializers.py`, `quizzes/test_regressions.py` | Preserve existing submission serializer; omit pre-attempt explanation hints; test existing API authentication, ownership, pagination, malformed input and server scoring |
| `dashboard/views.py`, `dashboard/tests.py`, `templates/dashboard/dashboard.html` | Owner-scoped counts and up to five recent documents, notes, active quizzes and results; empty states; bounded queries (at most 11 including auth in the regression test) |
| `templates/base.html`, `static/css/site.css` | Add missing Notes/resource navigation, shared messages and local responsive styles matching existing template classes |
| `requirements.txt` | Declare already-used `langchain-text-splitters==1.1.3`; retain existing dependency pins |
| `README.md`, `docs/REQUIREMENTS_AUDIT.md`, this report | Correct chunk sizes/defaults and document actual architecture, model relationships, workflows, setup, API, checks and limitations; update the existing README draft in place |

`quizzes/api_urls.py`, `quizzes/api_views.py` and the existing edit in `quizzes/tests.py`
were preserved. No new Quiz API architecture was created. No model, migration or existing
embedding-model/provider replacement was necessary. Source-reference support fixes a verified
gap in the existing Quiz implementation; server scoring and quiz lifecycle are preserved.

## C. Tests and validation

Commands used the repository's `venv/bin/python` (Python 3.12.3).
`PYTHONDONTWRITEBYTECODE=1` was used for final commands to avoid changing tracked caches.

| Command / check | Observed result |
| --- | --- |
| Initial `manage.py check` | No issues |
| Initial `manage.py showmigrations` | All existing migrations applied |
| Initial plain `manage.py test` | Discovered 61; interrupted after Hugging Face DNS retries stalled model initialization |
| `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ... manage.py test` before edits | 61 passed, 59.757 seconds, cached real embedding model |
| Intermediate `manage.py test quizzes ai_assistant` | Original 61 passed after initial fixes; transient static-directory warning resolved when stylesheet directory was created |
| `manage.py test accounts subjects notes documents` | 35 passed |
| `manage.py test ai_assistant.test_reliability dashboard` | 26 passed |
| Initial `manage.py test quizzes.test_regressions` | 11 passed |
| Final targeted `manage.py test quizzes.test_regressions config.tests` | 15 passed, including malformed difficulty and production settings |
| Final full `manage.py test` | **137 passed**, 63.663 seconds; no network/model download required |
| Final `manage.py check` | No issues |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `manage.py migrate --check` | Exit 0; no pending migrations |
| `python -m pip check` | No broken installed requirements |
| `manage.py findstatic css/site.css --verbosity 0` | Resolves repository stylesheet |
| Production import with debug false and no secret | Rejected with the intended configuration error |
| `manage.py check --deploy` with temporary production environment values | Exit 0 after SMTP fix; one `security.W004` HSTS warning remains intentionally unconfigured pending actual HTTPS hosting |
| `git diff --check` | Reports only the pre-existing extra blank line at EOF in `quizzes/tests.py`; excluding that preserved file passes |

Ordinary final tests mock external API/model work and require no network or real API key.
Expected failure-case log messages do not indicate failed tests. Tests use isolated databases
and temporary uploads; the working SQLite database, existing PDFs and migrations were retained.
Tracked bytecode changed by early Python commands was restored to its originally clean bytes.

At the end of the initial audit, live Gemini/account/model availability, fresh dependency
installation/model download, SMTP delivery, browser rendering and production hosting were
unverified. Browser launchers initially failed on Snap permissions. The subsequent UI work
resolved local browser verification using the Chromium binary directly; see [UI_REVIEW.md](UI_REVIEW.md).
Screenshots use explicitly synthetic fixtures. Live AI and deployment are still unverified.

## D. Security

- Registration now applies the existing Django password validators. CSRF middleware and
  token-protected forms remain enabled; anonymous and cross-user access are tested.
- Downloads use the authenticated document lookup; direct media URLs no longer resolve
  through this Django configuration. Deployment must also keep media storage private.
- The hardcoded Django key was removed. Environment variables configure production
  credentials and debug/hosts, with secure cookies and HTTPS redirects when debug is off.
- PDF signature, extension, size and extraction checks reject common invalid inputs.
- Provider errors and generated study material are no longer printed by LLM/RAG handling.
  The existing API omits explanations and correct-choice indexes before an attempt.
- A limited known-key/private-key pattern scan of tracked text found no matches. `.env`,
  `db.sqlite3` and `media/` are ignored and untracked. This is not an audit of all Git history
  or a guarantee that every possible credential format has been detected.

The retry implementation uses the installed [google-genai SDK error classes](https://github.com/googleapis/python-genai/blob/main/google/genai/errors.py)
and exponential backoff for transient statuses, consistent with [Google's guidance](https://ai.google.dev/gemini-api/docs/troubleshooting).
Registration invokes Django's [password-validation mechanism](https://docs.djangoproject.com/en/dev/topics/auth/passwords/).

This remains a targeted security review. Rate limits, malware scanning, resource isolation,
quotas and production monitoring are not implemented. Default debug mode supports local
development and must explicitly be disabled for public hosting. Set a stable development
secret to avoid sessions resetting on restart.

## E. Remaining work

### Required before portfolio publication

1. Run a live demonstration using a nonprivate, small PDF and a privately configured Gemini
   key/model; confirm summary, grounded Q&A, generated sources and quiz/result behavior.
2. **Completed in the UI follow-up:** actual screenshots and desktop/mobile Chromium rendering
   checks. Broader assistive-technology and cross-browser review remains recommended.
3. Validate installation in a clean environment with network access. The existing pinned
   manifest includes large platform-specific Torch/CUDA dependencies; only the installed
   environment was verified here.
4. Review the final source diff, retained local changes and public repository contents.

### Recommended improvements

- Measure synchronous PDF extraction/embedding/AI latency and expanded-document resource
  use before serving untrusted or larger workloads. The 10 MB upload cap does not bound
  expanded text or CPU/memory use.
- File storage is not transactional. A database failure after a new file write can leave an
  orphan file, and deleting records retains stored PDF bytes. Add a separately reviewed
  storage-retention/cleanup process, without deleting existing files as part of this audit.
- Chat sources retain text snapshots. Quiz references use chunk IDs; old excerpts can be
  unavailable after successful reprocessing replaces those chunks. Legacy quiz questions
  may have empty source lists.
- Before deployment, configure HTTPS/static serving, private media, backups and monitoring;
  review HSTS, proxy trust and SMTP with real hosting settings. No deployment is claimed.
- Remove already tracked Python bytecode from version control in a separately reviewed
  repository cleanup; no tracked cache files were deleted in this work.

### Optional future enhancements

Dedicated study analytics, cross-module search, OCR, a measured background queue,
PostgreSQL/vector indexing, CI and additional APIs only when product needs justify them.

## F. Git summary

Branch: `main`. After the audit and UI work, the user explicitly authorized separate
commits. The work is organized into six commits: core reliability, Quiz/API behavior,
environment configuration, the study-journal UI/dashboard, browser verification artifacts,
and documentation. The pre-existing Quiz API edits are included. No push, reset or migration
application was performed.

Existing modified tracked Python bytecode and the blank-line-only change in `quizzes/tests.py`
are intentionally left uncommitted. Use `git log --oneline -6` for the resulting commit hashes
and `git status --short` for remaining working-tree changes.

Earlier suggested aggregate commit message (the work was subsequently split):

```text
Fix study workflows and AI reliability, protect PDFs, and complete dashboard
```

## G. Next step

Run one live end-to-end demonstration with a nonprivate sample PDF and the configured
Gemini account, capturing screenshots while verifying summary, cited Q&A, quiz generation
and answer review. This closes the largest remaining gap beyond deterministic tests.


## UI follow-up

The user subsequently authorized a full UI improvement. Shared templates now provide a
responsive navigation, consistent form/resource/reading layouts, local light/dark
themes, PDF-selection feedback, source expansion/copying, quiz progress and submission states.
The implementation remains server-rendered Django with local CSS/JavaScript and SVG icons;
no frontend framework, new dependency, schema change or provider change was introduced.

After the UI work, the full Django suite again passed **137 tests in 63.590 seconds**.
Browser results, screenshots, reproduction commands and precise limitations are recorded in
[UI_REVIEW.md](UI_REVIEW.md). Existing user data and pre-existing edits remain preserved.


### Distinct study-journal revision

The user then requested a distinct identity from their CV maker. The final interface uses
a journal masthead and numbered horizontal index, paper/ink/rust colors, serif headings,
a typographic `s/a` mark, a reading-pile overview, margin notes, a document index, and file-like
subject and exercise layouts. The earlier promotional hero, pastel tile system and desktop
sidebar have been replaced. Existing mobile drawer, filtering, file feedback and quiz behavior
are retained. No changes were made to the CV maker repository.

The final full suite passed **137 tests in 64.538 seconds**. Browser checks passed 102 assertions
with no console errors. The focused run initially caught a percentage string split across
markup; the template was corrected and the existing assertions were kept. The final screenshots
and design details are in [UI_REVIEW.md](UI_REVIEW.md).
