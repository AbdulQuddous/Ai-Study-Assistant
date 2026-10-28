# Study journal design — 2026-10-28

The user requested a distinct identity after reviewing the first UI, and explicitly chose
to differentiate this application from the CV maker. The current design is a personal study
journal: warm paper, ink blue, rust annotations, serif reading typography, monospaced index
labels, and thin rules. A custom `s/a` wordmark anchors the masthead. Desktop navigation is
a horizontal, numbered index; phones use the existing accessible drawer.

The desk features a reading pile, a document cover based on the actual latest document title,
notes in a margin column, and simple quiz/result records. Library documents appear as an
indexed list; subjects resemble labeled files; notes and practice sets use paper proportions.
Counts and content continue to come from the authenticated user's data.

This revision changes templates and local CSS. Existing JavaScript interactions, Django
services, permissions, model/provider choices and data are preserved. No package was added.

## What changed

- **Navigation:** a masthead and numbered desktop index, active sections, breadcrumbs,
  account access, a mobile drawer, an explicit
  close button, Escape handling, focus containment, and restoration of focus on close.
- **The desk:** a typographic greeting, a plain collection ledger, a lead reading file,
  margin notes, recent quizzes/results and direct document/note actions. No promotional
  banner or decorative activity metrics are used.
- **Authentication and forms:** consistent labels, visible validation errors, optional/required
  indicators, password visibility controls, submission feedback and larger mobile inputs.
- **Libraries:** readable subject/note/document/quiz cards; instant client-side filters for
  currently listed subjects, documents and quizzes. Notes retain existing server-side search
  and pagination, including query preservation.
- **Writing and reading:** focused note/document pages, a note word counter, copy controls,
  expandable extracted text, clearer document actions, and specific deletion confirmations.
- **PDF uploads:** a drag-and-drop area with an accessible native file picker, filename/size
  feedback and client-side extension/size checks. Server validation remains authoritative.
  Processing shows an honest pending state without a fabricated percentage.
- **AI conversations:** optional question suggestions, a character counter, answer cards,
  expandable source excerpts, copy actions and a reminder to verify important information.
- **Practice quizzes:** larger selectable choices, live answered counts, progress and question
  shortcuts; an optional unanswered-question review before submission; clear result states,
  explanations and source excerpts. Scoring remains on the server.
- **Preferences and motion:** only the visual theme is saved in localStorage. Study content
  and answers are not persisted by the UI script. Reduced-motion preferences are respected.

Most navigation, forms, source expansion and submission remain ordinary HTML. JavaScript
adds convenience interactions. Submission controls recover when returning through browser
history, and forms keep their existing CSRF tokens and ownership-protected endpoints.

## Verification

| Check | Observed result |
| --- | --- |
| Full Django suite after template refresh | **137 passed in 64.538 seconds** |
| Intermediate focused regression suite | 73 ran; one percentage-markup assertion failed and was corrected in the template; tests were retained |
| Dashboard after correction | **4 passed**, including percentages, query bound and ownership |
| Chromium browser checks | **102 assertions passed**, no browser console errors |
| Desktop rendering | 17 pages rendered through the actual Django views using synthetic fixtures |
| Responsive layouts | No horizontal overflow on checked 390px screens; additional checks at 320px |
| Interactions | Theme persistence, list filtering/clearing, question suggestions/counter, source expansion, password visibility, word counts, file feedback, quiz progress/confirmation/loading, browser-history recovery, drawer buttons/Tab/Escape |
| Secondary text contrast | `#626660` on paper `#f1eee5`: approximately **5.04:1**, calculated locally |
| JavaScript syntax | `node --check static/js/app.js` passed |
| Django system check | No issues |
| Static assets | `css/site.css` and `js/app.js` resolve through Django static discovery |

The browser checks load rendered HTML previews and the real local assets. Form navigation
is canceled in the loading-state checks; the Django suite separately verifies request handling,
permissions, persistence and scoring. These checks do not constitute a live Gemini test,
a complete accessibility audit, or cross-browser certification. Clipboard support depends on
browser permissions; the UI offers a select-and-copy fallback message when unavailable.

The Snap launchers were unavailable inside the sandbox. Chromium's installed executable
was run directly with approved local browser execution. No packages were installed.

## Screenshots

All screenshots below are actual browser captures at 1440px desktop or 390px mobile widths,
using **synthetic demonstration data in an isolated in-memory database**. The sample summary,
questions and answers are presentation fixtures. They were not generated by a live AI call.
No working database records, uploaded PDFs, private account information or API keys were used.

| Screen | Desktop | Mobile |
| --- | --- | --- |
| Dashboard | [Light](screenshots/dashboard-desktop.png) · [Dark](screenshots/dashboard-dark.png) | [Mobile](screenshots/dashboard-mobile.png) |
| Subjects | [Subject files](screenshots/subjects-desktop.png) | Responsive styles checked |
| Notes | [Notebook](screenshots/notes-desktop.png) | Checked in browser |
| Library | [Document index](screenshots/documents-desktop.png) | Checked in browser |
| Practice sets | [Exercise sheets](screenshots/quizzes-desktop.png) | Responsive styles checked |
| PDF upload | [Upload](screenshots/upload-desktop.png) | Checked in browser |
| Document | [Summary and actions](screenshots/document-desktop.png) | Checked in browser |
| Ask AI | [Conversation](screenshots/qa-desktop.png) | [Mobile](screenshots/qa-mobile.png) |
| Quiz | [Practice](screenshots/quiz-desktop.png) | [Mobile](screenshots/quiz-mobile.png) |
| Results | [Answer review](screenshots/result-desktop.png) | Checked in browser |
| Sign in | [Login](screenshots/login-desktop.png) | [Mobile](screenshots/login-mobile.png) |

The individual browser assertions are saved in
[screenshots/browser-results.json](screenshots/browser-results.json).

## Reproduce the review

Use the existing Python environment. The scripts need Chromium/Chrome and a compatible
ChromeDriver installed on the machine; they use Python's standard library for WebDriver
requests and do not require Selenium or Playwright. The browser script uses a loopback-only
WebDriver port and temporary HTML previews, then closes the browser and removes previews.

```bash
# Check JavaScript syntax and Django behavior.
node --check static/js/app.js
PYTHONDONTWRITEBYTECODE=1 venv/bin/python manage.py check
PYTHONDONTWRITEBYTECODE=1 venv/bin/python manage.py test

# Render previews without opening a browser or changing the working database.
PYTHONDONTWRITEBYTECODE=1 venv/bin/python scripts/render_ui_preview.py \
  --output-dir /tmp/study-ui-preview

# Run the browser assertions and refresh synthetic screenshots.
PYTHONDONTWRITEBYTECODE=1 venv/bin/python scripts/check_ui_browser.py
```

If automatic browser discovery does not match your installation, provide explicit paths:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python scripts/check_ui_browser.py \
  --browser /path/to/chrome --driver /path/to/chromedriver \
  --screenshots-dir /tmp/study-ui-screenshots
```

For ordinary local use, run `venv/bin/python manage.py runserver` and sign in normally.
Production still requires the previously documented hosting/static/media configuration.
