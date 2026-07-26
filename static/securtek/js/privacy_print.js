(function () {
    const modal = document.getElementById("privacyPrintModal");
    if (!modal) {
        return;
    }

    const statusEl = modal.querySelector("[data-privacy-status]");
    const warningEl = modal.querySelector("[data-privacy-warning]");
    const warningTextEl = modal.querySelector("[data-privacy-warning-text]");
    const previewEl = modal.querySelector("[data-privacy-preview]");
    const printBtn = modal.querySelector("[data-privacy-print]");
    const downloadBtn = modal.querySelector("[data-privacy-download]");
    const closeButtons = modal.querySelectorAll("[data-privacy-close]");
    const titleEl = document.getElementById("privacyPrintTitle");

    let pageImages = [];

    function setStatus(message, isError) {
        if (!statusEl) {
            return;
        }
        statusEl.hidden = !message;
        statusEl.textContent = message || "";
        statusEl.classList.toggle("text-danger", !!isError);
        statusEl.classList.toggle("text-secondary", !isError);
    }

    function setDocumentoWarning(message) {
        if (!warningEl) {
            return;
        }
        const text = (message || "").trim();
        if (warningTextEl) {
            warningTextEl.textContent = text;
        }
        warningEl.hidden = !text;
    }

    function openModal() {
        modal.hidden = false;
        document.body.classList.add("st-privacy-open");
    }

    function closeModal() {
        modal.hidden = true;
        document.body.classList.remove("st-privacy-open");
        pageImages = [];
        if (previewEl) {
            previewEl.innerHTML = "";
            previewEl.hidden = true;
        }
        if (printBtn) {
            printBtn.hidden = true;
        }
        if (downloadBtn) {
            downloadBtn.hidden = true;
            downloadBtn.removeAttribute("href");
        }
        setDocumentoWarning("");
        setStatus("Preparazione scheda…", false);
    }

    function renderPreview(images) {
        if (!previewEl) {
            return;
        }
        previewEl.innerHTML = "";
        images.forEach(function (src, index) {
            const img = document.createElement("img");
            img.src = src;
            img.alt = "Pagina " + (index + 1);
            previewEl.appendChild(img);
        });
        previewEl.hidden = false;
    }

    function privacyPrintStylesheet() {
        return (
            "@page { size: A4 portrait; margin: 0; }" +
            "html, body { margin: 0; padding: 0; background: #fff; }" +
            ".privacy-print-page { width: 210mm; height: 297mm; overflow: hidden; page-break-inside: avoid; break-inside: avoid; }" +
            ".privacy-print-page + .privacy-print-page { page-break-before: always; break-before: page; }" +
            ".privacy-print-page img { display: block; width: 100%; height: 100%; object-fit: contain; }"
        );
    }

    function buildPrivacyPrintBody(images) {
        var html = "";
        images.forEach(function (src, index) {
            html +=
                '<div class="privacy-print-page">' +
                '<img src="' +
                src +
                '" alt="Pagina ' +
                (index + 1) +
                '">' +
                "</div>";
        });
        return html;
    }

    function printPages(images) {
        if (!images.length) {
            return;
        }
        var html =
            "<!DOCTYPE html><html><head><meta charset='utf-8'>" +
            "<title>Scheda Privacy</title>" +
            "<style>" +
            privacyPrintStylesheet() +
            "</style></head><body>" +
            buildPrivacyPrintBody(images) +
            "</body></html>";

        // Iframe nascosto: niente scheda nuova e niente URL in barra.
        var frame = document.getElementById("privacyPrintFrame");
        if (frame) {
            frame.remove();
        }
        frame = document.createElement("iframe");
        frame.id = "privacyPrintFrame";
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

        var imgs = doc.images;
        if (!imgs || !imgs.length) {
            setTimeout(trigger, 200);
            return;
        }
        var pending = imgs.length;
        function done() {
            pending -= 1;
            if (pending <= 0) {
                setTimeout(trigger, 100);
            }
        }
        for (var i = 0; i < imgs.length; i++) {
            if (imgs[i].complete) {
                done();
            } else {
                imgs[i].onload = done;
                imgs[i].onerror = done;
            }
        }
    }

    async function loadPrivacy(url) {
        openModal();
        setDocumentoWarning("");
        setStatus("Salvataggio scheda…", false);
        if (printBtn) {
            printBtn.hidden = true;
        }
        if (downloadBtn) {
            downloadBtn.hidden = true;
        }
        if (previewEl) {
            previewEl.hidden = true;
            previewEl.innerHTML = "";
        }

        try {
            if (typeof window.labrepairSavePraticaForm === "function") {
                await window.labrepairSavePraticaForm();
            }

            setStatus("Preparazione scheda…", false);
            const separator = url.indexOf("?") >= 0 ? "&" : "?";
            const response = await fetch(url + separator + "format=json", {
                credentials: "same-origin",
                headers: { Accept: "application/json" },
            });
            const payload = await response.json().catch(function () {
                return {};
            });
            if (!response.ok || !payload.ok) {
                throw new Error(payload.message || "Impossibile preparare la scheda Privacy.");
            }

            pageImages = payload.page_images || [];
            if (titleEl && payload.title) {
                titleEl.textContent = payload.title;
            }
            renderPreview(pageImages);
            setStatus("", false);
            if (payload.documento_scaduto && payload.documento_scaduto_warning) {
                setDocumentoWarning(payload.documento_scaduto_warning);
            } else {
                setDocumentoWarning("");
            }

            if (downloadBtn && payload.pdf_url) {
                downloadBtn.href = payload.pdf_url;
                downloadBtn.download = payload.filename || "Scheda_Privacy.pdf";
                downloadBtn.hidden = false;
            }
            if (printBtn) {
                printBtn.hidden = false;
            }
        } catch (error) {
            setDocumentoWarning("");
            setStatus(error.message || "Errore durante la preparazione.", true);
        }
    }

    document.querySelectorAll("[data-privacy-open]").forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            const url = button.getAttribute("href") || button.dataset.privacyUrl || "";
            if (!url) {
                return;
            }
            loadPrivacy(url);
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
            printPages(pageImages);
        });
    }
})();
