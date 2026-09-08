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
    let stampanteNome = "";
    let agentUrl = "http://127.0.0.1:17346";
    let skipFinalSave = false;

    function isDirectPrint() {
        return document.body.getAttribute("data-busta-stampa-diretta") === "1";
    }

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
        stampanteNome = "";
        skipFinalSave = false;
        if (previewEl) {
            previewEl.innerHTML = "";
            previewEl.hidden = true;
        }
        if (printBtn) {
            printBtn.hidden = true;
        }
        setStatus("Preparazione busta…", false);
    }

    function clearPendingFotoInputs(form) {
        if (!form) {
            return;
        }
        form.querySelectorAll('input[type="file"]').forEach(function (input) {
            input.value = "";
        });
    }

    function adoptCreatedPratica(payload) {
        const form = document.getElementById("praticaForm");
        if (!form || !payload) {
            return;
        }
        if (payload.edit_url) {
            form.setAttribute("action", payload.edit_url);
        }
        // Evita di ricaricare le stesse foto su un eventuale secondo salvataggio.
        clearPendingFotoInputs(form);
        const reserved = form.querySelector('input[name="codice_riservato"]');
        if (reserved) {
            reserved.remove();
        }
    }

    async function fetchCssText(cssUrl) {
        if (!cssUrl) {
            return "";
        }

        try {
            const response = await fetch(cssUrl, { credentials: "same-origin" });
            if (!response.ok) {
                return "";
            }

            let cssText = await response.text();
            const cssBase = cssUrl.split("?")[0].replace(/[^/]+$/, "");
            const fontsBase = cssBase.replace(/css\/$/, "fonts/");
            cssText = cssText.replace(/url\((["']?)\.\.\/fonts\//g, "url($1" + fontsBase);
            return cssText;
        } catch (error) {
            return "";
        }
    }

    async function buildDocument(sheetHtml, cssUrl) {
        const cssText = await fetchCssText(cssUrl);
        const styleBlock = cssText
            ? "<style>" + cssText + "</style>"
            : "<link rel='stylesheet' href='" + cssUrl + "'>";

        return (
            "<!DOCTYPE html><html lang='it'><head><meta charset='utf-8'>" +
            "<title>Busta riparazione</title>" +
            styleBlock +
            "</head><body>" +
            sheetHtml +
            "</body></html>"
        );
    }

    function waitForStylesheets(doc, callback) {
        const links = doc.querySelectorAll("link[rel='stylesheet']");
        if (!links.length) {
            callback();
            return;
        }

        let pending = links.length;
        let done = false;

        function finish() {
            pending -= 1;
            if (pending <= 0 && !done) {
                done = true;
                callback();
            }
        }

        links.forEach(function (link) {
            if (link.sheet) {
                finish();
                return;
            }
            link.addEventListener("load", finish);
            link.addEventListener("error", finish);
        });

        setTimeout(function () {
            if (!done) {
                done = true;
                callback();
            }
        }, 3000);
    }

    function waitForFonts(doc, callback) {
        const fonts = doc.fonts;
        if (fonts && fonts.ready) {
            fonts.ready
                .then(function () {
                    setTimeout(callback, 150);
                })
                .catch(function () {
                    setTimeout(callback, 300);
                });
            return;
        }
        setTimeout(callback, 300);
    }

    function waitForPrintReady(doc, callback) {
        waitForStylesheets(doc, function () {
            waitForFonts(doc, callback);
        });
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

    function printDocumentBrowser(html) {
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

        waitForPrintReady(doc, trigger);
    }

    async function printViaAgent(html, printerName) {
        const base = (agentUrl || "http://127.0.0.1:17346").replace(/\/$/, "");
        let response;
        try {
            response = await fetch(base + "/print", {
                method: "POST",
                credentials: "omit",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    printer: printerName,
                    html: html,
                }),
            });
        } catch (error) {
            throw new Error(agentUnreachableMessage());
        }
        const payload = await response.json().catch(function () {
            return {};
        });
        if (!response.ok || !payload.ok) {
            throw new Error(
                payload.message ||
                    "Impossibile stampare tramite l'agent locale."
            );
        }
        return payload;
    }

    function agentUnreachableMessage() {
        const base = (agentUrl || "http://127.0.0.1:17346").replace(/\/$/, "");
        return (
            "Agent stampanti non raggiungibile (" +
            base +
            "). Avvia LabRepair Printer Agent su questo PC, " +
            "poi premi di nuovo Stampa. In alternativa puoi usare la stampa del browser."
        );
    }

    function friendlyErrorMessage(error) {
        const msg = (error && error.message) || "";
        if (/failed to fetch|networkerror|load failed|network request failed/i.test(msg)) {
            return agentUnreachableMessage();
        }
        return msg || "Errore durante la stampa.";
    }

    function showPrintReady(html, statusMessage, isError) {
        printHtml = html || printHtml;
        if (printHtml) {
            renderPreview(printHtml);
        }
        setStatus(statusMessage || "", !!isError);
        if (printBtn) {
            printBtn.hidden = !printHtml;
        }
    }

    function markFormCleanForLeave() {
        if (typeof window.labrepairPraticaFormMarkClean === "function") {
            window.labrepairPraticaFormMarkClean();
        }
    }

    function getReturnUrl() {
        const fromModal = (modal.getAttribute("data-busta-return-url") || "").trim();
        if (fromModal) {
            return fromModal;
        }
        const cancelLink = document.querySelector("[data-pratica-annulla]");
        if (cancelLink && cancelLink.getAttribute("href")) {
            return cancelLink.getAttribute("href");
        }
        return "/pratiche/";
    }

    async function saveAndReturnToList() {
        const form = document.getElementById("praticaForm");
        const returnUrl = getReturnUrl();

        if (!skipFinalSave) {
            setStatus("Salvataggio scheda…", false);
            if (form && typeof window.labrepairSavePraticaForm === "function") {
                await window.labrepairSavePraticaForm({ skipClientValidation: true });
            }
        }

        markFormCleanForLeave();
        setStatus(
            skipFinalSave
                ? "Riparazione salvata. Ritorno all'elenco…"
                : "Scheda salvata. Ritorno all'elenco…",
            false
        );
        window.location.assign(returnUrl);
    }

    async function printDocument(html) {
        if (!html) {
            return;
        }
        if (!stampanteNome) {
            throw new Error(
                "Nessuna stampante buste attiva per questa postazione. " +
                    "Impostala in Parametri PC → Stampanti → flag «Stampante buste»."
            );
        }

        setStatus("Stampa su " + stampanteNome + "…", false);
        try {
            const result = await printViaAgent(html, stampanteNome);
            setStatus(result.message || ("Busta inviata a " + stampanteNome), false);
            await saveAndReturnToList();
        } catch (error) {
            const message = friendlyErrorMessage(error);
            showPrintReady(html, message, true);
            if (printBtn) {
                printBtn.dataset.fallbackBrowser = "1";
            }
            throw new Error(message);
        }
    }

    async function printThenReturnToList(html) {
        /**
         * Usato da «Stampa busta + Salva»: stampa subito (senza restare in anteprima)
         * e torna sempre all'elenco perché la riparazione è già salvata.
         */
        printHtml = html || printHtml;
        if (!printHtml) {
            throw new Error("Documento busta non disponibile.");
        }
        if (!stampanteNome) {
            throw new Error(
                "Nessuna stampante buste attiva per questa postazione. " +
                    "Impostala in Parametri PC → Stampanti → flag «Stampante buste»."
            );
        }

        setStatus("Stampa su " + stampanteNome + "…", false);
        try {
            const result = await printViaAgent(printHtml, stampanteNome);
            setStatus(
                (result.message || ("Busta inviata a " + stampanteNome)) +
                    " Ritorno all'elenco…",
                false
            );
        } catch (error) {
            setStatus(
                friendlyErrorMessage(error) + " Apro la stampa del browser…",
                true
            );
            printDocumentBrowser(printHtml);
            await new Promise(function (resolve) {
                window.setTimeout(resolve, 1200);
            });
        }

        skipFinalSave = true;
        markFormCleanForLeave();
        await saveAndReturnToList();
    }

    async function loadBusta(url, options) {
        options = options || {};
        const form = document.getElementById("praticaForm");
        const skipSave = !!options.skipSave;

        // 1) Coerenza dati: blocca subito (senza modal) se manca qualcosa.
        if (!skipSave && form && typeof window.labrepairValidatePraticaForm === "function") {
            const validation = window.labrepairValidatePraticaForm();
            if (!validation.ok) {
                return;
            }
        }

        // Flag PC «Stampa busta senza anteprima» → stampa diretta; altrimenti anteprima + Stampa.
        const directPrint = isDirectPrint();
        openModal();
        setStatus(
            !skipSave && form ? "Salvataggio scheda…" : "Preparazione busta…",
            false
        );
        if (printBtn) {
            printBtn.hidden = true;
            delete printBtn.dataset.fallbackBrowser;
            delete printBtn.dataset.returnOnly;
            printBtn.innerHTML = '<i class="ti ti-printer"></i> Stampa';
        }
        if (previewEl) {
            previewEl.hidden = true;
            previewEl.innerHTML = "";
        }

        try {
            // 2) Salvataggio automatico della scheda (stessa validazione di Salva).
            if (!skipSave && form && typeof window.labrepairSavePraticaForm === "function") {
                const saved = await window.labrepairSavePraticaForm({
                    skipClientValidation: true,
                });
                if (saved && saved.busta_url && !url) {
                    url = saved.busta_url;
                }
                if (saved && saved.edit_url) {
                    adoptCreatedPratica(saved);
                }
                setStatus("Scheda salvata. Preparazione busta…", false);
            } else {
                setStatus("Preparazione busta…", false);
            }

            if (!url) {
                throw new Error("URL busta non disponibile.");
            }

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

            stampanteNome = (payload.stampante_nome || "").trim();
            agentUrl = (payload.agent_url || "http://127.0.0.1:17346").trim();
            printHtml = await buildDocument(payload.sheet_html || "", payload.css_url || "");

            if (!stampanteNome) {
                throw new Error(
                    "Nessuna stampante buste attiva per questa postazione. " +
                        "Impostala in Parametri PC → Stampanti → flag «Stampante buste»."
                );
            }

            if (directPrint) {
                // Senza anteprima: stampa e torna all'elenco.
                if (skipFinalSave) {
                    await printThenReturnToList(printHtml);
                } else {
                    try {
                        await printDocument(printHtml);
                    } catch (error) {
                        setStatus(friendlyErrorMessage(error), true);
                    }
                }
                return;
            }

            // Con anteprima: salva già fatto → mostra busta e attendi conferma Stampa.
            renderPreview(printHtml);
            setStatus(
                skipFinalSave
                    ? "Riparazione salvata. Controlla la busta e premi Stampa."
                    : "Stampante buste: " + stampanteNome,
                false
            );
            if (printBtn) {
                printBtn.hidden = false;
            }
        } catch (error) {
            const message = friendlyErrorMessage(error);
            setStatus(message, true);
            if (printHtml) {
                showPrintReady(printHtml, message, true);
                if (printBtn) {
                    printBtn.dataset.fallbackBrowser = "1";
                }
            } else if (printBtn) {
                printBtn.hidden = true;
            }
        }
    }

    async function saveNewAndPrintBusta() {
        const form = document.getElementById("praticaForm");
        if (!form) {
            return;
        }

        if (typeof window.labrepairValidatePraticaForm === "function") {
            const validation = window.labrepairValidatePraticaForm();
            if (!validation.ok) {
                return;
            }
        } else if (typeof form.reportValidity === "function" && !form.reportValidity()) {
            return;
        }

        if (typeof window.labrepairSavePraticaForm !== "function") {
            return;
        }

        openModal();
        setStatus("Salvataggio riparazione…", false);
        if (printBtn) {
            printBtn.hidden = true;
            delete printBtn.dataset.fallbackBrowser;
            delete printBtn.dataset.returnOnly;
            printBtn.innerHTML = '<i class="ti ti-printer"></i> Stampa';
        }
        if (previewEl) {
            previewEl.hidden = true;
            previewEl.innerHTML = "";
        }

        try {
            const saved = await window.labrepairSavePraticaForm({
                skipClientValidation: true,
            });
            if (!saved || !saved.ok) {
                throw new Error(
                    (saved && saved.message) ||
                        "Impossibile salvare la riparazione."
                );
            }
            if (!saved.busta_url) {
                throw new Error("Riparazione salvata, ma URL busta non disponibile.");
            }
            adoptCreatedPratica(saved);
            markFormCleanForLeave();
            // Riparazione già salvata: stampa secondo flag PC (diretta o con anteprima).
            skipFinalSave = true;
            setStatus("Riparazione salvata. Preparazione busta…", false);
            await loadBusta(saved.busta_url, { skipSave: true });
        } catch (error) {
            setStatus(
                friendlyErrorMessage(error) ||
                    "Impossibile salvare e stampare la busta.",
                true
            );
            const action = (form.getAttribute("action") || "").trim();
            if (action && action.indexOf("/modifica") >= 0) {
                if (printBtn) {
                    printBtn.hidden = false;
                    printBtn.innerHTML = '<i class="ti ti-list"></i> Torna all\'elenco';
                    printBtn.dataset.returnOnly = "1";
                }
            } else if (printBtn) {
                printBtn.hidden = true;
            }
        }
    }

    document.querySelectorAll("[data-busta-open]").forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            const url = button.getAttribute("href") || button.dataset.bustaUrl || "";
            if (!url) {
                return;
            }
            skipFinalSave = false;
            loadBusta(url);
        });
    });

    document.querySelectorAll("[data-busta-save-print]").forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            saveNewAndPrintBusta();
        });
    });

    closeButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const formEl = document.getElementById("praticaForm");
            const action = formEl ? formEl.getAttribute("action") || "" : "";
            // Dopo creazione riuscita, Chiudi torna all'elenco.
            if (skipFinalSave || action.indexOf("/modifica") >= 0) {
                markFormCleanForLeave();
                window.location.assign(getReturnUrl());
                return;
            }
            closeModal();
        });
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
            if (printBtn.dataset.returnOnly === "1") {
                skipFinalSave = true;
                markFormCleanForLeave();
                window.location.assign(getReturnUrl());
                return;
            }

            const html = printHtml;
            const useBrowserFallback = printBtn.dataset.fallbackBrowser === "1";

            printDocument(html).catch(function (error) {
                if (useBrowserFallback && html) {
                    setStatus(
                        friendlyErrorMessage(error) +
                            " Apro la stampa del browser…",
                        true
                    );
                    printDocumentBrowser(html);
                    window.setTimeout(function () {
                        skipFinalSave = true;
                        markFormCleanForLeave();
                        saveAndReturnToList().catch(function () {
                            window.location.assign(getReturnUrl());
                        });
                    }, 1000);
                    return;
                }
                setStatus(friendlyErrorMessage(error), true);
            });
        });
    }
})();
