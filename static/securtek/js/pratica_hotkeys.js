(function () {
    function readHotkeys() {
        const body = document.body;
        if (!body) {
            return null;
        }
        return {
            salva: (body.getAttribute("data-pratica-hotkey-salva") || "").trim(),
            annulla: (body.getAttribute("data-pratica-hotkey-annulla") || "").trim(),
            busta: (body.getAttribute("data-pratica-hotkey-busta") || "").trim(),
            privacy: (body.getAttribute("data-pratica-hotkey-privacy") || "").trim(),
            riparatore: (body.getAttribute("data-pratica-hotkey-riparatore") || "").trim(),
            tipoOggetto: (body.getAttribute("data-pratica-hotkey-tipo-oggetto") || "").trim(),
        };
    }

    function normalizeToken(token) {
        const value = String(token || "").trim().toLowerCase();
        if (value === "control" || value === "ctrl") {
            return "ctrl";
        }
        if (value === "escape" || value === "esc") {
            return "esc";
        }
        if (value === " " || value === "space" || value === "spacebar") {
            return "space";
        }
        if (value === "return") {
            return "enter";
        }
        return value;
    }

    function parseShortcut(shortcut) {
        const raw = String(shortcut || "").trim();
        if (!raw) {
            return null;
        }
        const parts = raw.split("+").map(normalizeToken).filter(Boolean);
        if (!parts.length) {
            return null;
        }
        const key = parts[parts.length - 1];
        return {
            ctrl: parts.includes("ctrl"),
            shift: parts.includes("shift"),
            alt: parts.includes("alt") || parts.includes("altgraph"),
            meta: parts.includes("meta") || parts.includes("cmd") || parts.includes("command"),
            key: key,
        };
    }

    function eventKeyToken(event) {
        if (event.key === "Escape") {
            return "esc";
        }
        if (event.key === "Enter") {
            return "enter";
        }
        if (event.key === " ") {
            return "space";
        }
        if (/^f\d{1,2}$/i.test(event.key)) {
            return event.key.toLowerCase();
        }
        if (event.key && event.key.length === 1) {
            return event.key.toLowerCase();
        }
        return (event.key || "").toLowerCase();
    }

    function matchesShortcut(event, shortcut) {
        const parsed = parseShortcut(shortcut);
        if (!parsed) {
            return false;
        }
        const key = eventKeyToken(event);
        if (!key || key !== parsed.key) {
            return false;
        }
        return (
            !!event.ctrlKey === parsed.ctrl &&
            !!event.shiftKey === parsed.shift &&
            !!event.altKey === parsed.alt &&
            !!event.metaKey === parsed.meta
        );
    }

    function isHidden(el) {
        if (!el) {
            return true;
        }
        if (el.hidden || el.getAttribute("aria-hidden") === "true") {
            return true;
        }
        if (el.closest("[hidden], [aria-hidden='true']")) {
            return true;
        }
        const style = window.getComputedStyle(el);
        return style.display === "none" || style.visibility === "hidden";
    }

    function isModalOpen() {
        const body = document.body;
        if (body.classList.contains("st-busta-open") || body.classList.contains("st-privacy-open")) {
            return true;
        }
        const webcamModal = document.getElementById("webcamCaptureModal");
        if (webcamModal && !webcamModal.hidden) {
            return true;
        }
        const confirmModal = document.querySelector(".st-confirm:not([hidden])");
        if (confirmModal) {
            return true;
        }
        return document.body.classList.contains("st-anagrafica-overlay-open");
    }

    function buttonLabel(btn) {
        return String(btn.textContent || btn.value || "")
            .replace(/\s+/g, " ")
            .trim()
            .toLowerCase();
    }

    function getPrimarySaveButton(form) {
        if (!form) {
            return null;
        }
        const buttons = Array.from(
            form.querySelectorAll('button[type="submit"], input[type="submit"]')
        );
        const saveLike = buttons.filter(function (btn) {
            if (btn.disabled || isHidden(btn)) {
                return false;
            }
            if (
                btn.classList.contains("btn-danger") ||
                btn.classList.contains("btn-outline-danger") ||
                btn.classList.contains("btn-secondary") ||
                btn.classList.contains("btn-outline-secondary") ||
                btn.classList.contains("btn-outline-primary")
            ) {
                return false;
            }
            const label = buttonLabel(btn);
            return /\b(salva|conferma)\b/.test(label);
        });
        return saveLike[0] || null;
    }

    function isSaveableForm(form) {
        if (!form || form.dataset.hotkeySalva === "0") {
            return false;
        }
        if (isHidden(form)) {
            return false;
        }
        if ((form.getAttribute("method") || form.method || "get").toLowerCase() !== "post") {
            return false;
        }
        if (form.closest(".st-confirm, .modal")) {
            return false;
        }
        return Boolean(getPrimarySaveButton(form));
    }

    function findSaveForm() {
        const preferred = document.getElementById("praticaForm") || document.getElementById("anagraficaForm");
        if (preferred && isSaveableForm(preferred)) {
            return preferred;
        }

        const marked = document.querySelector("form[data-hotkey-salva]");
        if (marked && isSaveableForm(marked)) {
            return marked;
        }

        const active = document.activeElement;
        if (active && typeof active.closest === "function") {
            const focusedForm = active.closest("form");
            if (focusedForm && isSaveableForm(focusedForm)) {
                return focusedForm;
            }
        }

        const candidates = Array.from(document.querySelectorAll("form")).filter(isSaveableForm);
        return candidates[0] || null;
    }

    function clickFirst(selector) {
        const el = document.querySelector(selector);
        if (!el || el.disabled || el.getAttribute("aria-disabled") === "true") {
            return false;
        }
        el.click();
        return true;
    }

    function focusField(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field || field.disabled || field.getAttribute("aria-disabled") === "true") {
            return false;
        }
        field.focus({ preventScroll: false });
        if (typeof field.showPicker === "function" && field.tagName === "SELECT") {
            try {
                field.showPicker();
            } catch (_err) {
                // showPicker non supportato o rifiutato: il focus basta.
            }
        }
        return true;
    }

    function saveForm(form) {
        if (!form) {
            return false;
        }
        const submitBtn = getPrimarySaveButton(form);
        if (submitBtn && typeof form.requestSubmit === "function") {
            form.requestSubmit(submitBtn);
            return true;
        }
        if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
            return true;
        }
        if (submitBtn) {
            submitBtn.click();
            return true;
        }
        form.submit();
        return true;
    }

    function annotateSaveButtons(hotkey) {
        if (!hotkey) {
            return;
        }
        const hotkeyNorm = hotkey.toLowerCase();
        document.querySelectorAll("form").forEach(function (form) {
            if (!isSaveableForm(form)) {
                return;
            }
            const btn = getPrimarySaveButton(form);
            if (!btn || btn.dataset.hotkeyAnnotated === "1") {
                return;
            }
            btn.dataset.hotkeyAnnotated = "1";
            if (buttonLabel(btn).indexOf(hotkeyNorm) !== -1 || btn.querySelector(".st-hotkey-hint")) {
                return;
            }
            if (!btn.title) {
                btn.title = "Scorciatoia: " + hotkey;
            }
            const hint = document.createElement("span");
            hint.className = "st-hotkey-hint opacity-75";
            hint.textContent = " (" + hotkey + ")";
            btn.appendChild(hint);
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.defaultPrevented || event.isComposing || isModalOpen()) {
            return;
        }

        const hotkeys = readHotkeys();
        if (!hotkeys) {
            return;
        }

        if (matchesShortcut(event, hotkeys.salva)) {
            const form = findSaveForm();
            if (!form) {
                return;
            }
            event.preventDefault();
            saveForm(form);
            return;
        }

        const praticaForm = document.getElementById("praticaForm");
        const anagraficaForm = document.getElementById("anagraficaForm");

        if (matchesShortcut(event, hotkeys.annulla)) {
            if (!praticaForm && !anagraficaForm) {
                return;
            }
            event.preventDefault();
            if (anagraficaForm) {
                clickFirst("[data-embed-close], [data-anagrafica-annulla]");
            } else {
                clickFirst("[data-pratica-annulla]");
            }
            return;
        }

        if (!praticaForm) {
            return;
        }
        if (matchesShortcut(event, hotkeys.busta)) {
            event.preventDefault();
            if (!clickFirst("[data-busta-open]")) {
                clickFirst("[data-busta-save-print]");
            }
            return;
        }
        if (matchesShortcut(event, hotkeys.privacy)) {
            event.preventDefault();
            clickFirst("[data-privacy-open]");
            return;
        }
        if (matchesShortcut(event, hotkeys.riparatore)) {
            event.preventDefault();
            focusField("id_riparatore");
            return;
        }
        if (matchesShortcut(event, hotkeys.tipoOggetto)) {
            event.preventDefault();
            focusField("id_tipo_oggetto");
        }
    });

    function boot() {
        const hotkeys = readHotkeys();
        if (hotkeys && hotkeys.salva) {
            annotateSaveButtons(hotkeys.salva);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
