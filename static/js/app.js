/* Small progressive enhancements. Django remains responsible for data and scoring. */
(() => {
    'use strict';
    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
    const root = document.documentElement;
    const toast = $('#ui-toast');
    let toastTimeout;
    const notify = (message) => {
        if (!toast) return;
        toast.textContent = message;
        toast.hidden = false;
        clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => { toast.hidden = true; }, 4000);
    };

    // Only the visual preference is persisted; no study content enters localStorage.
    const themeButtons = $$('[data-theme-toggle]');
    const updateThemeLabels = () => themeButtons.forEach(button => {
        const dark = root.dataset.theme === 'dark';
        button.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} theme`);
        button.setAttribute('aria-pressed', String(dark));
    });
    themeButtons.forEach(button => button.addEventListener('click', () => {
        root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('study-theme', root.dataset.theme); } catch (_) { /* Storage is optional. */ }
        updateThemeLabels();
    }));
    updateThemeLabels();

    const sidebar = $('#sidebar');
    const menuButton = $('[data-menu-toggle]');
    const backdrop = $('[data-close-sidebar]');
    const workspaceBody = $('.workspace-body');
    const mobile = window.matchMedia('(max-width: 760px)');
    const setMenu = (open, restoreFocus = true) => {
        if (!sidebar || !menuButton) return;
        sidebar.classList.toggle('is-open', open);
        menuButton.setAttribute('aria-expanded', String(open));
        menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
        document.body.classList.toggle('nav-open', open && mobile.matches);
        sidebar.inert = mobile.matches && !open;
        if (workspaceBody) workspaceBody.inert = mobile.matches && open;
        if (backdrop) backdrop.hidden = !open || !mobile.matches;
        if (open && mobile.matches) $('a', sidebar)?.focus();
        else if (restoreFocus && mobile.matches) menuButton.focus();
    };
    menuButton?.addEventListener('click', () => setMenu(!sidebar.classList.contains('is-open')));
    backdrop?.addEventListener('click', () => setMenu(false));
    $('[data-sidebar-close]')?.addEventListener('click', () => setMenu(false));
    mobile.addEventListener('change', () => setMenu(false, false));
    setMenu(false, false);
    document.addEventListener('keydown', event => {
        if (!mobile.matches || !sidebar?.classList.contains('is-open')) return;
        if (event.key === 'Escape') { setMenu(false); return; }
        if (event.key === 'Tab') {
            const focusable = $$('a[href], button:not([disabled])', sidebar);
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        }
    });
    $$('[data-dismiss-message]').forEach(button => button.addEventListener('click', () => button.closest('.notification')?.remove()));

    $$('input[type="password"]').forEach(input => {
        const wrapper = document.createElement('div');
        wrapper.className = 'password-wrapper';
        input.before(wrapper);
        wrapper.append(input);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'password-toggle';
        button.textContent = 'Show';
        button.setAttribute('aria-controls', input.id);
        button.setAttribute('aria-label', `Show ${input.name.replaceAll('_', ' ')}`);
        button.setAttribute('aria-pressed', 'false');
        wrapper.append(button);
        button.addEventListener('click', () => {
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            button.textContent = show ? 'Hide' : 'Show';
            button.setAttribute('aria-pressed', String(show));
            button.setAttribute('aria-label', `${show ? 'Hide' : 'Show'} ${input.name.replaceAll('_', ' ')}`);
        });
    });
    $$('textarea[maxlength]').forEach(input => {
        const counter = document.createElement('span');
        counter.className = 'character-count';
        input.after(counter);
        const update = () => { counter.textContent = `${input.value.length} / ${input.maxLength} characters`; };
        input.addEventListener('input', update);
        update();
    });
    const noteContent = $('textarea[name="content"]');
    const wordCount = $('[data-word-count]');
    if (noteContent && wordCount) {
        const update = () => {
            const words = noteContent.value.trim().split(/\s+/).filter(Boolean).length;
            wordCount.textContent = `${words} ${words === 1 ? 'word' : 'words'}`;
        };
        noteContent.addEventListener('input', update);
        update();
    }

    $$('[data-filter-input]').forEach(input => {
        const target = document.getElementById(input.dataset.filterInput);
        if (!target) return;
        const cards = $$('[data-filter-card]', target);
        const empty = document.getElementById(input.dataset.filterEmpty);
        const count = document.getElementById(input.dataset.filterCount);
        input.addEventListener('input', () => {
            const query = input.value.trim().toLocaleLowerCase();
            let matches = 0;
            cards.forEach(card => {
                card.hidden = !card.textContent.toLocaleLowerCase().includes(query);
                if (!card.hidden) matches += 1;
            });
            if (empty) empty.hidden = matches !== 0;
            if (count) count.textContent = `${matches} ${matches === 1 ? 'item' : 'items'}`;
        });
    });
    $$('[data-clear-filter]').forEach(button => button.addEventListener('click', () => {
        const input = document.getElementById(button.dataset.clearFilter);
        if (!input) return;
        input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
    }));

    $$('[data-file-drop]').forEach(zone => {
        const input = $('input[type="file"]', zone);
        const feedback = $('[data-file-feedback]', zone);
        if (!input || !feedback) return;
        input.accept = '.pdf,application/pdf';
        const update = () => {
            const file = input.files[0];
            input.setCustomValidity('');
            feedback.classList.remove('invalid');
            if (!file) { feedback.textContent = ''; return; }
            let error = '';
            if (!file.name.toLowerCase().endsWith('.pdf')) error = 'Please choose a PDF file.';
            else if (file.size > 10 * 1024 * 1024) error = 'This file is too large. Choose a PDF of 10 MB or less.';
            else if (!file.size) error = 'This file is empty. Choose another PDF.';
            input.setCustomValidity(error);
            feedback.classList.toggle('invalid', Boolean(error));
            feedback.textContent = error || `${file.name} · ${(file.size / (1024 * 1024)).toFixed(2)} MB · Ready to upload`;
        };
        input.addEventListener('change', update);
        ['dragenter', 'dragover'].forEach(name => zone.addEventListener(name, event => {
            event.preventDefault(); zone.classList.add('is-dragging');
        }));
        ['dragleave', 'drop'].forEach(name => zone.addEventListener(name, event => {
            event.preventDefault(); zone.classList.remove('is-dragging');
        }));
        zone.addEventListener('drop', event => {
            if (!event.dataTransfer?.files.length) return;
            try {
                const transfer = new DataTransfer();
                transfer.items.add(event.dataTransfer.files[0]);
                input.files = transfer.files;
                update();
            } catch (_) { feedback.textContent = 'Choose your PDF using the file picker below.'; }
        });
    });
    $$('[data-question-suggestion]').forEach(button => button.addEventListener('click', () => {
        const question = $('textarea[name="question"]');
        if (!question) return;
        question.value = button.dataset.questionSuggestion;
        question.dispatchEvent(new Event('input', { bubbles: true }));
        question.focus();
    }));
    $$('[data-copy-target]').forEach(button => button.addEventListener('click', async () => {
        const target = document.getElementById(button.dataset.copyTarget);
        if (!target) return;
        try {
            await navigator.clipboard.writeText(target.innerText);
            notify('Copied to clipboard.');
        } catch (_) { notify('Copy is unavailable here. You can select and copy the text.'); }
    }));

    const quizForm = $('#quiz-form');
    const quizQuestions = quizForm ? $$('[data-question]', quizForm) : [];
    const progress = $('#quiz-progress');
    const answeredLabel = $('[data-answered-count]');
    const answeredCount = () => quizQuestions.filter(question => $('input:checked', question)).length;
    const updateProgress = () => {
        const answered = answeredCount();
        if (progress) progress.value = answered;
        if (answeredLabel) answeredLabel.textContent = `${answered} of ${quizQuestions.length} answered`;
        quizQuestions.forEach(question => {
            const link = $(`[data-question-link="${question.id}"]`);
            const selected = Boolean($('input:checked', question));
            link?.classList.toggle('is-answered', selected);
            link?.setAttribute('aria-label', `Question ${question.dataset.question}: ${selected ? 'answered' : 'not answered'}`);
        });
    };
    quizForm?.addEventListener('change', updateProgress);
    updateProgress();
    const reviewDialog = $('#quiz-review-dialog');
    $('[data-continue-quiz]')?.addEventListener('click', () => reviewDialog?.close());
    $('[data-confirm-submit]')?.addEventListener('click', () => {
        if (!quizForm) return;
        reviewDialog.close();
        quizForm.dataset.confirmed = 'true';
        quizForm.requestSubmit();
    });
    const resetLoading = () => {
        $$('form[data-submitting]').forEach(form => {
            delete form.dataset.submitting;
            delete form.dataset.confirmed;
            form.removeAttribute('aria-busy');
        });
        $$('[data-original-label]').forEach(button => {
            button.disabled = false;
            button.replaceChildren(...button._originalNodes);
            delete button.dataset.originalLabel;
        });
        $$('[data-loading-status]').forEach(status => { status.hidden = true; });
    };
    window.addEventListener('pageshow', resetLoading);
    document.addEventListener('submit', event => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || event.defaultPrevented) return;
        if (form.dataset.submitting) { event.preventDefault(); return; }
        if (form === quizForm && !form.dataset.confirmed && reviewDialog && typeof reviewDialog.showModal === 'function') {
            const missing = quizQuestions.length - answeredCount();
            if (missing > 0) {
                event.preventDefault();
                $('[data-unanswered-message]', reviewDialog).textContent = `${missing} ${missing === 1 ? 'question is' : 'questions are'} unanswered. You can go back and finish, or submit now. Unanswered questions count as incorrect.`;
                reviewDialog.showModal();
                return;
            }
        }
        if (!form.hasAttribute('data-loading')) return;
        form.dataset.submitting = 'true';
        form.setAttribute('aria-busy', 'true');
        $$('button[type="submit"]', form).forEach(button => {
            button._originalNodes = [...button.childNodes];
            button.dataset.originalLabel = 'true';
            const spinner = document.createElement('span');
            spinner.className = 'spinner';
            spinner.setAttribute('aria-hidden', 'true');
            const label = document.createElement('span');
            label.textContent = form.dataset.loading || 'Working…';
            button.replaceChildren(spinner, label);
            button.disabled = true;
        });
        const status = $('[data-loading-status]', form);
        if (status) status.hidden = false;
    });
})();
