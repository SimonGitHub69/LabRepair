(function () {
    const overlay = document.getElementById("nuovoClienteOverlay");
    if (!overlay) {
        return;
    }

    const frame = overlay.querySelector("[data-nuovo-cliente-frame]");
    const errorBox = overlay.querySelector("[data-nuovo-cliente-error]");
    const closeButtons = overlay.querySelectorAll("[data-nuovo-cliente-close]");

    function embedUrl(url) {
        const parsed = new URL(url, window.location.href);
        parsed.searchParams.set("embed", "1");
        if (!parsed.searchParams.get("tipo")) {
            parsed.searchParams.set("tipo", "cliente");
        }
        return parsed.href;
    }

    function hideError() {
        if (errorBox) {
            errorBox.hidden = true;
        }
    }

    function showError() {
        if (errorBox) {
            errorBox.hidden = false;
        }
    }

    function openOverlay(url) {
        hideError();
        overlay.hidden = false;
        document.body.classList.add("st-anagrafica-overlay-open");
        const next = embedUrl(url);
        window.requestAnimationFrame(function () {
            frame.src = next;
        });
    }

    function closeOverlay() {
        overlay.hidden = true;
        document.body.classList.remove("st-anagrafica-overlay-open");
        frame.src = "about:blank";
        hideError();
    }

    document.addEventListener("click", function (event) {
        const link = event.target.closest(".js-nuovo-cliente-link");
        if (!link) {
            return;
        }
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
            return;
        }
        event.preventDefault();
        openOverlay(link.href);
    });

    closeButtons.forEach(function (btn) {
        btn.addEventListener("click", function () {
            closeOverlay();
        });
    });

    frame.addEventListener("load", function () {
        if (overlay.hidden) {
            return;
        }
        try {
            const href = frame.contentWindow && frame.contentWindow.location
                ? String(frame.contentWindow.location.href || "")
                : "";
            if (!href || href === "about:blank") {
                return;
            }
            hideError();
            window.setTimeout(function () {
                try {
                    const win = frame.contentWindow;
                    const doc = frame.contentDocument;
                    if (!win || !doc) {
                        return;
                    }
                    const form = doc.getElementById("anagraficaForm");
                    if (!form || form.dataset.anagraficaNuovo !== "1") {
                        return;
                    }
                    const cognome = doc.getElementById("id_cognome");
                    if (!cognome || cognome.disabled) {
                        return;
                    }
                    win.focus();
                    cognome.focus();
                } catch (focusError) {
                    // iframe non ancora accessibile
                }
            }, 40);
        } catch (error) {
            showError();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape" || overlay.hidden) {
            return;
        }
        if (event.target && event.target.closest(".st-confirm")) {
            return;
        }
        event.preventDefault();
        closeOverlay();
    });

    window.addEventListener("message", function (event) {
        if (event.origin !== window.location.origin) {
            return;
        }
        const data = event.data || {};
        if (data.type === "labrepair:anagrafica-embed-close") {
            closeOverlay();
            return;
        }
        if (data.type === "labrepair:anagrafica-embed-done") {
            if (data.id && typeof window.labrepairSelectCliente === "function") {
                window.labrepairSelectCliente(data.id, data.label || "");
            }
            closeOverlay();
        }
    });
})();
