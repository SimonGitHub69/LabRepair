(function () {
    const modal = document.getElementById("bustaPrintModal");
    if (!modal) {
        return;
    }

    const statusEl = modal.querySelector("[data-busta-status]");
    const previewEl = modal.querySelector("[data-busta-preview]");
    const printBtn = modal.querySelector("[data-busta-print]");
    const closeButtons = modal.querySelectorAll("[data-busta-close]");
    const titleEl = document.getElementById("bustaPrintTitle");

    let printHtml = "";

    function setStatus(message, isError) {
        if (!statusEl) {
            return;
        }
        statusEl.hidden = !message;
        statusEl.textContent = message || "";
        statusEl.classList.toggle("text-danger", !!isError);
        statusEl.classList.toggle("text-secondary", !isError);
    }

    function openModal() {
        modal.hidden = false;
        document.body.classList.add("st-busta-open");
    }

    function closeModal() {
        modal.hidden = true;
        document.body.classList.remove("st-busta-open");
        printHtml = "";
        if (previewEl) {
            previewEl.innerHTML = "";
            previewEl.hidden = true;
        }
        if (printBtn) {
            printBtn.hidden = true;
        }
        setStatus("Preparazione busta…", false);
    }

    function buildDocument(sheetHtml, cssUrl) {
        return (
            "<!DOCTYPE html><html lang='it'><head><meta charset='utf-8'>" +
            "<title>Busta riparazione</title>" +
            "<link rel='stylesheet' href='" +
            cssUrl +
            "'>" +
            "</head><body>" +
            sheetHtml +
            "</body></html>"
        );
    }

    function renderPreview(html) {
        if (!previewEl) {
            return;
        }
        previewEl.innerHTML = "";
        var frame = document.createElement("iframe");
        frame.title = "Anteprima busta";
        frame.setAttribute("aria-label", "Anteprima busta");
        previewEl.appendChild(frame);
        var doc = frame.contentDocument || frame.contentWindow.document;
        doc.open();
        doc.write(html);
        doc.close();
        previewEl.hidden = false;
    }

    function printDocument(html) {
        if (!html) {
            return;
        }

        var frame = document.getElementById("bustaPrintFrame");
        if (frame) {
            frame.remove();
        }
        frame = document.createElement("iframe");
        frame.id = "bustaPrintFrame";
        frame.setAttribute("aria-hidden", "true");
        frame.style.cssText =
            "position:fixed;right:0;bottom:0;width:0;height:0;border:0;opacity:0;pointer-events:none;";
        document.body.appendChild(frame);

        var doc = frame.contentDocument || frame.contentWindow.document;
        doc.open();
        doc.write(html);
        doc.close();

        function trigger() {
            try {
                frame.contentWindow.focus();
                frame.contentWindow.print();
            } catch (err) {
                alert("Impossibile aprire la stampa.");
            }
        }

        function readyPrint() {
            var fonts = doc.fonts;
            if (fonts && fonts.ready) {
                fonts.ready
                    .then(function () {
                        setTimeout(trigger, 150);
                    })
                    .catch(function () {
                        setTimeout(trigger, 300);
                    });
            } else {
                setTimeout(trigger, 300);
            }
        }

        if (doc.readyState === "complete") {
            readyPrint();
        } else {
            frame.onload = readyPrint;
            setTimeout(readyPrint, 400);
        }
    }

    async function loadBusta(url) {
        openModal();
        setStatus("Salvataggio scheda…", false);
        if (printBtn) {
            printBtn.hidden = true;
        }
        if (previewEl) {
            previewEl.hidden = true;
            previewEl.innerHTML = "";
        }

        try {
            if (typeof window.labrepairSavePraticaForm === "function") {
                await window.labrepairSavePraticaForm();
            }

            setStatus("Preparazione busta…", false);
            const separator = url.indexOf("?") >= 0 ? "&" : "?";
            const response = await fetch(url + separator + "format=json", {
                credentials: "same-origin",
                headers: { Accept: "application/json" },
            });
            const payload = await response.json().catch(function () {
                return {};
            });
            if (!response.ok || !payload.ok) {
                throw new Error(payload.message || "Impossibile preparare la busta.");
            }

            if (titleEl && payload.title) {
                titleEl.textContent = payload.title;
            }

            printHtml = buildDocument(payload.sheet_html || "", payload.css_url || "");
            renderPreview(printHtml);
            setStatus("", false);
            if (printBtn) {
                printBtn.hidden = false;
            }
        } catch (error) {
            setStatus(error.message || "Errore durante la preparazione.", true);
        }
    }

    document.querySelectorAll("[data-busta-open]").forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            const url = button.getAttribute("href") || button.dataset.bustaUrl || "";
            if (!url) {
                return;
            }
            loadBusta(url);
        });
    });

    closeButtons.forEach(function (button) {
        button.addEventListener("click", closeModal);
    });

    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modal.hidden) {
            closeModal();
        }
    });

    if (printBtn) {
        printBtn.addEventListener("click", function () {
            printDocument(printHtml);
        });
    }
})();
