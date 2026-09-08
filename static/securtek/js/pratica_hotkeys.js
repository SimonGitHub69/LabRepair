(function () {
    const form = document.getElementById("praticaForm");
    if (!form) {
        return;
    }

    function readHotkeys() {
        const body = document.body;
        return {
            salva: (body.getAttribute("data-pratica-hotkey-salva") || "").trim(),
            annulla: (body.getAttribute("data-pratica-hotkey-annulla") || "").trim(),
            busta: (body.getAttribute("data-pratica-hotkey-busta") || "").trim(),
            privacy: (body.getAttribute("data-pratica-hotkey-privacy") || "").trim(),
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
        return !!confirmModal;
    }

    function clickFirst(selector) {
        const el = document.querySelector(selector);
        if (!el || el.disabled || el.getAttribute("aria-disabled") === "true") {
            return false;
        }
        el.click();
        return true;
    }

    function saveForm() {
        if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
            return true;
        }
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.click();
            return true;
        }
        form.submit();
        return true;
    }

    document.addEventListener("keydown", function (event) {
        if (event.defaultPrevented || event.isComposing || isModalOpen()) {
            return;
        }

        const hotkeys = readHotkeys();
        if (matchesShortcut(event, hotkeys.salva)) {
            event.preventDefault();
            saveForm();
            return;
        }
        if (matchesShortcut(event, hotkeys.annulla)) {
            event.preventDefault();
            clickFirst("[data-pratica-annulla]");
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
        }
    });
})();
