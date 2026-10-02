(function () {
    const modal = document.getElementById("bustaPrintModal");
    if (!modal) {
        return;
    }

    const statusEl = modal.querySelector("[data-busta-status]");
    const previewEl = modal.querySelector("[data-busta-preview]");
    const printBtn = modal.querySelector("[data-busta-print]");
    const printBrowserBtn = modal.querySelector("[data-busta-print-browser]");
    const closeButtons = modal.querySelectorAll("[data-busta-close]");
    const titleEl = document.getElementById("bustaPrintTitle");

    let printHtml = "";
    let stampanteNome = "";
    let agentUrl = "http://127.0.0.1:17346";
    let stampataUrl = "";
    let bustaMarked = false;
    let skipFinalSave = false;
    let forceSave = false;

    function isDirectPrint() {
        return document.body.getAttribute("data-busta-stampa-diretta") === "1";
    }

    function wantsSave() {
        if (forceSave) {
            return true;
        }
        // Parametri PC: default sì se attributo assente.
        return document.body.getAttribute("data-busta-stampa-salva") !== "0";
    }

    function wantsReturnToList() {
        return document.body.getAttribute("data-busta-stampa-torna-elenco") === "1";
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
        forceSave = false;
        if (previewEl) {
            previewEl.innerHTML = "";
            previewEl.hidden = true;
        }
        if (printBtn) {
            printBtn.hidden = true;
        }
        hideBrowserFallback();
        setStatus("Preparazione busta…", false);
    }

    function localAgentFetch(url, options) {
        options = options || {};
        options.credentials = "omit";
        // Chrome Local Network Access: origine LAN → 127.0.0.1.
        options.targetAddressSpace = "loopback";
        return fetch(url, options);
    }

    function hideBrowserFallback() {
        if (printBtn) {
            delete printBtn.dataset.fallbackBrowser;
        }
        if (printBrowserBtn) {
            printBrowserBtn.hidden = true;
        }
    }

    function showBrowserFallback() {
        if (printBtn) {
            printBtn.dataset.fallbackBrowser = "1";
        }
        if (printBrowserBtn && printHtml) {
            printBrowserBtn.hidden = false;
        }
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
        if (
            payload.cliente_id &&
            typeof window.labrepairSelectCliente === "function"
        ) {
            window.labrepairSelectCliente(
                payload.cliente_id,
                payload.cliente_label || ""
            );
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
            response = await localAgentFetch(base + "/print", {
                method: "POST",
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
            "poi premi di nuovo Stampa. Oppure usa «Stampa dal browser»."
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

    function csrfToken() {
        const input = document.querySelector(
            '#praticaForm input[name="csrfmiddlewaretoken"]'
        );
        if (input && input.value) {
            return input.value;
        }
        const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    async function markBustaStampata() {
        if (bustaMarked) {
            if (typeof window.labrepairLockCliente === "function") {
                window.labrepairLockCliente();
            }
            return;
        }
        if (!stampataUrl) {
            return;
        }
        try {
            const response = await fetch(stampataUrl, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": csrfToken(),
                    Accept: "application/json",
                },
            });
            if (!response.ok) {
                return;
            }
            const payload = await response.json().catch(function () {
                return {};
            });
            bustaMarked = true;
            if (typeof window.labrepairLockCliente === "function") {
                window.labrepairLockCliente(payload);
            }
        } catch (error) {
            // La stampa è già partita: un errore di rete non deve bloccare il seguito.
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

    async function finishAfterPrint(statusMessage) {
        if (wantsReturnToList()) {
            if (statusMessage) {
                setStatus(statusMessage, false);
            }
            await saveAndReturnToList();
            return;
        }

        if (skipFinalSave || !wantsSave()) {
            // Scheda già coerente oppure stampa senza nuovo salvataggio.
        } else {
            markFormCleanForLeave();
        }

        setStatus(
            (statusMessage ? statusMessage + " " : "") +
                "Puoi continuare sulla scheda.",
            false
        );
        window.setTimeout(function () {
            closeModal();
        }, 900);
    }

    async function saveAndReturnToList() {
        const form = document.getElementById("praticaForm");
        const returnUrl = getReturnUrl();

        if (!skipFinalSave && wantsSave()) {
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

    async function fetchBustaDocument(url) {
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
        if ((payload.stampata_url || "").trim()) {
            stampataUrl = payload.stampata_url.trim();
        }
        printHtml = await buildDocument(payload.sheet_html || "", payload.css_url || "");
        if (!stampanteNome) {
            throw new Error(
                "Nessuna stampante buste attiva per questa postazione. " +
                    "Impostala in Parametri PC → Stampanti → flag «Stampante buste»."
            );
        }
        return payload;
    }

    function cancelledError(message) {
        const err = new Error(message || "Operazione annullata.");
        err.labrepairCancelled = true;
        return err;
    }

    function isCancelledError(error) {
        return !!(error && error.labrepairCancelled);
    }

    async function ensureTelefonoForSave() {
        if (
            typeof window.labrepairNeedsSenzaTelefonoForce === "function" &&
            window.labrepairNeedsSenzaTelefonoForce()
        ) {
            const forza =
                typeof window.labrepairPromptSenzaTelefonoForce === "function"
                    ? await window.labrepairPromptSenzaTelefonoForce()
                    : false;
            if (!forza) {
                return false;
            }
        }
        return true;
    }

    async function maybeSaveBeforePrint() {
        if (skipFinalSave || !wantsSave()) {
            return null;
        }
        const form = document.getElementById("praticaForm");
        if (!form || typeof window.labrepairSavePraticaForm !== "function") {
            return null;
        }
        if (!(await ensureTelefonoForSave())) {
            throw cancelledError();
        }
        if (typeof window.labrepairValidatePraticaForm === "function") {
            const validation = window.labrepairValidatePraticaForm();
            if (!validation.ok) {
                if (validation.reason === "telefono") {
                    if (!(await ensureTelefonoForSave())) {
                        throw cancelledError();
                    }
                } else {
                    throw new Error(
                        validation.message ||
                            "Compila i campi obbligatori prima di stampare."
                    );
                }
            }
        }
        setStatus("Salvataggio scheda…", false);
        const saved = await window.labrepairSavePraticaForm({
            skipClientValidation: true,
        });
        if (saved && saved.edit_url) {
            adoptCreatedPratica(saved);
        }
        markFormCleanForLeave();
        return saved;
    }

    async function printDocument(html) {
        if (!html && !printHtml) {
            return;
        }
        try {
            const saved = await maybeSaveBeforePrint();
            if (saved && saved.busta_url) {
                await fetchBustaDocument(saved.busta_url);
                html = printHtml;
            }
        } catch (error) {
            if (isCancelledError(error)) {
                return;
            }
            const message = friendlyErrorMessage(error);
            showPrintReady(printHtml || html, message, true);
            throw new Error(message);
        }

        html = html || printHtml;
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
            const message = result.message || ("Busta inviata a " + stampanteNome);
            setStatus(message, false);
            await markBustaStampata();
            await finishAfterPrint(message);
        } catch (error) {
            const message = friendlyErrorMessage(error);
            showPrintReady(html, message, true);
            showBrowserFallback();
            throw new Error(message);
        }
    }

    async function printThenFinish(html) {
        /**
         * Stampa immediata (senza restare in anteprima), poi elenco o resta in scheda
         * secondo l'opzione «Torna all'elenco».
         */
        try {
            const saved = await maybeSaveBeforePrint();
            if (saved && saved.busta_url) {
                await fetchBustaDocument(saved.busta_url);
                html = printHtml;
            }
        } catch (error) {
            if (isCancelledError(error)) {
                throw error;
            }
            setStatus(friendlyErrorMessage(error), true);
            throw error;
        }
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
        let message = "";
        try {
            const result = await printViaAgent(printHtml, stampanteNome);
            message = result.message || ("Busta inviata a " + stampanteNome);
            setStatus(message, false);
            await markBustaStampata();
        } catch (error) {
            setStatus(
                friendlyErrorMessage(error) + " Apro la stampa del browser…",
                true
            );
            printDocumentBrowser(printHtml);
            await markBustaStampata();
            await new Promise(function (resolve) {
                window.setTimeout(resolve, 1200);
            });
            message = "Stampa browser aperta.";
        }

        skipFinalSave = true;
        await finishAfterPrint(message);
    }

    async function loadBusta(url, options) {
        options = options || {};
        // skipSave: scheda appena salvata (es. «Stampa busta + Salva»).
        // Altrimenti, se Parametri PC richiede salvataggio, salva prima dell'anteprima
        // così la busta mostra le modifiche correnti del form.

        // Conferme (es. telefono) PRIMA del modal busta, altrimenti restano sotto e bloccano.
        if (!options.skipSave && !skipFinalSave && wantsSave()) {
            if (!(await ensureTelefonoForSave())) {
                return;
            }
        }

        // Flag PC «Stampa busta senza anteprima» → stampa diretta; altrimenti anteprima + Stampa.
        const directPrint = isDirectPrint();
        openModal();
        setStatus("Preparazione busta…", false);
        if (printBtn) {
            printBtn.hidden = true;
            delete printBtn.dataset.returnOnly;
            printBtn.innerHTML = '<i class="ti ti-printer"></i> Stampa';
        }
        hideBrowserFallback();
        if (previewEl) {
            previewEl.hidden = true;
            previewEl.innerHTML = "";
        }

        try {
            if (!options.skipSave && !skipFinalSave && wantsSave()) {
                const saved = await maybeSaveBeforePrint();
                if (saved && saved.busta_url) {
                    url = saved.busta_url;
                }
                // Evita un secondo salvataggio al click Stampa.
                skipFinalSave = true;
            }

            await fetchBustaDocument(url);

            if (directPrint) {
                // Senza anteprima: stampa e poi elenco o resta in scheda.
                try {
                    await printThenFinish(printHtml);
                } catch (error) {
                    if (isCancelledError(error)) {
                        closeModal();
                        return;
                    }
                    setStatus(friendlyErrorMessage(error), true);
                    showPrintReady(printHtml, friendlyErrorMessage(error), true);
                    showBrowserFallback();
                }
                return;
            }

            // Con anteprima: mostra busta e attendi conferma Stampa.
            renderPreview(printHtml);
            setStatus(
                skipFinalSave
                    ? "Scheda aggiornata. Controlla la busta e premi Stampa."
                    : "Stampante buste: " +
                          stampanteNome +
                          ". Anteprima sui dati già salvati (Parametri PC: salvataggio disattivo).",
                false
            );
            if (printBtn) {
                printBtn.hidden = false;
            }
        } catch (error) {
            if (isCancelledError(error)) {
                closeModal();
                return;
            }
            const message = friendlyErrorMessage(error);
            setStatus(message, true);
            if (printHtml) {
                showPrintReady(printHtml, message, true);
                showBrowserFallback();
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

        forceSave = true;

        if (!(await ensureTelefonoForSave())) {
            return;
        }

        if (typeof window.labrepairValidatePraticaForm === "function") {
            const validation = window.labrepairValidatePraticaForm();
            if (!validation.ok) {
                if (validation.reason === "telefono") {
                    if (!(await ensureTelefonoForSave())) {
                        return;
                    }
                } else {
                    return;
                }
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
            delete printBtn.dataset.returnOnly;
            printBtn.innerHTML = '<i class="ti ti-printer"></i> Stampa';
        }
        hideBrowserFallback();
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
            if (isCancelledError(error)) {
                closeModal();
                return;
            }
            setStatus(
                friendlyErrorMessage(error) ||
                    "Impossibile salvare e stampare la busta.",
                true
            );
            const action = (form.getAttribute("action") || "").trim();
            if (action && action.indexOf("/modifica") >= 0) {
                if (printBtn) {
                    printBtn.hidden = false;
                    printBtn.innerHTML = wantsReturnToList()
                        ? '<i class="ti ti-list"></i> Torna all\'elenco'
                        : '<i class="ti ti-check"></i> Continua in scheda';
                    printBtn.dataset.returnOnly = wantsReturnToList() ? "1" : "stay";
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
            forceSave = false;
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
            if (wantsReturnToList()) {
                const formEl = document.getElementById("praticaForm");
                const action = formEl ? formEl.getAttribute("action") || "" : "";
                // Dopo creazione riuscita, Chiudi torna all'elenco solo se richiesto.
                if (skipFinalSave || action.indexOf("/modifica") >= 0) {
                    markFormCleanForLeave();
                    window.location.assign(getReturnUrl());
                    return;
                }
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

    if (printBrowserBtn) {
        printBrowserBtn.addEventListener("click", function () {
            if (!printHtml) {
                return;
            }
            setStatus("Apro la stampa del browser…", false);
            printDocumentBrowser(printHtml);
            markBustaStampata();
            window.setTimeout(function () {
                skipFinalSave = true;
                finishAfterPrint("Stampa browser aperta.").catch(function () {
                    if (wantsReturnToList()) {
                        window.location.assign(getReturnUrl());
                    } else {
                        closeModal();
                    }
                });
            }, 1000);
        });
    }

    if (printBtn) {
        printBtn.addEventListener("click", function () {
            if (printBtn.dataset.returnOnly === "1") {
                skipFinalSave = true;
                markFormCleanForLeave();
                window.location.assign(getReturnUrl());
                return;
            }
            if (printBtn.dataset.returnOnly === "stay") {
                closeModal();
                return;
            }

            const html = printHtml;
            printDocument(html).catch(function (error) {
                if (isCancelledError(error)) {
                    return;
                }
                setStatus(friendlyErrorMessage(error), true);
                showBrowserFallback();
            });
        });
    }
})();
