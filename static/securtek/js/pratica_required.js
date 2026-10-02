(function () {
    const REQUIRED_FIELDS = [
        {
            id: "id_operatore",
            message: "Seleziona un operatore.",
        },
        {
            id: "id_cliente",
            focusId: "clienteSearchInput",
            message: "Seleziona un cliente oppure inserisci Nome e Cognome.",
            optionalIfNomeCognome: true,
        },
        {
            id: "id_referente_telefono",
            message: "Inserisci il telefono o il cellulare.",
            optionalIfTelefonoOrCellulare: true,
        },
        {
            id: "id_tipo_oggetto",
            message: "Seleziona un tipo oggetto.",
        },
        {
            id: "id_descrizione",
            message: "Inserisci la descrizione.",
        },
        {
            id: "id_data_scadenza",
            message: "Inserisci la data prevista consegna.",
            notBeforeToday: true,
            notBeforeTodayMessage:
                "La data prevista consegna non può essere precedente a oggi.",
        },
    ];

    const PESO_REQUIRED = {
        id: "id_peso_grammi",
        message: "Inserisci il peso quando è indicato il tipo di metallo.",
    };

    const CENTRO_REQUIRED = {
        id: "id_centro_assistenza",
        message: "Seleziona il centro assistenza.",
    };

    const PREZZO_PUBBLICO_REQUIRED = {
        id: "id_prezzo_al",
        message:
            "Con stato «In consegna» inserisci un Prezzo al Pubblico oppure seleziona Senza Spesa.",
        inConsegnaPrezzoPubblico: true,
    };

    function getField(config) {
        return document.getElementById(config.id);
    }

    function getFocusTarget(config) {
        if (config.focusId) {
            return document.getElementById(config.focusId);
        }
        const field = getField(config);
        if (field && field.classList.contains("st-date-native")) {
            const wrap = field.closest(".st-date-field");
            const text = wrap ? wrap.querySelector(".st-date-text") : null;
            if (text) {
                return text;
            }
        }
        return field;
    }

    function isPrezioso() {
        const tipologia = document.getElementById("id_tipologia");
        return Boolean(tipologia && tipologia.value === "prezioso");
    }

    function hasTipoMetallo() {
        const metallo = document.getElementById("id_tipo_metallo");
        return Boolean(metallo && String(metallo.value || "").trim());
    }

    function isAssistenzaRiparatore() {
        const riparatoreField = document.getElementById("id_riparatore");
        if (!riparatoreField) {
            return false;
        }
        const assistenzaId = riparatoreField.dataset.assistenzaRiparatoreId || "";
        return Boolean(assistenzaId && riparatoreField.value === String(assistenzaId));
    }

    function isInConsegna() {
        const select = document.getElementById("id_stato");
        if (select && select.tagName === "SELECT") {
            return select.value === "in_consegna";
        }
        const checked = document.querySelector(
            '#praticaForm input[type="radio"][name="stato"]:checked'
        );
        return Boolean(checked && checked.value === "in_consegna");
    }

    function isSenzaSpesa() {
        const flag = document.getElementById("id_senza_spesa");
        return Boolean(flag && flag.checked);
    }

    function parseAmount(value) {
        const normalized = String(value || "").replace(",", ".").trim();
        const amount = Number.parseFloat(normalized);
        return Number.isFinite(amount) ? amount : 0;
    }

    function fieldTrimmedValue(id) {
        const mirror = document.getElementById(id);
        const store = document.getElementById(id + "_store");
        const fromMirror = mirror ? String(mirror.value || "").trim() : "";
        const fromStore = store ? String(store.value || "").trim() : "";
        return fromMirror || fromStore;
    }

    function hasNomeECognome() {
        return Boolean(
            fieldTrimmedValue("id_referente_nome") &&
                fieldTrimmedValue("id_referente_cognome")
        );
    }

    function hasTelefonoOrCellulare() {
        return Boolean(
            fieldTrimmedValue("id_referente_telefono") ||
                fieldTrimmedValue("id_referente_cellulare")
        );
    }

    function getForzaSenzaTelefonoField() {
        return document.getElementById("id_forza_senza_telefono");
    }

    function isForzaSenzaTelefono() {
        const field = getForzaSenzaTelefonoField();
        return !!(field && String(field.value || "").trim() === "1");
    }

    function setForzaSenzaTelefono(on) {
        const field = getForzaSenzaTelefonoField();
        if (field) {
            field.value = on ? "1" : "";
        }
    }

    function clearTelefonoCellulareValidity() {
        ["id_referente_telefono", "id_referente_cellulare"].forEach(function (id) {
            const field = document.getElementById(id);
            if (field && typeof field.setCustomValidity === "function") {
                field.setCustomValidity("");
            }
        });
    }

    function focusTelefonoFields() {
        const telefono = document.getElementById("id_referente_telefono");
        const cellulare = document.getElementById("id_referente_cellulare");
        const target =
            telefono && !String(telefono.value || "").trim()
                ? telefono
                : cellulare || telefono;
        if (!target) {
            return;
        }
        target.focus({ preventScroll: true });
        if (!window.labrepairSuppressFieldBlurUi) {
            target.scrollIntoView({ behavior: "auto", block: "center" });
        }
    }

    function buildSenzaTelefonoMessage() {
        return (
            "Non è stato inserito un <strong>telefono</strong> o un <strong>cellulare</strong>." +
            "<br><br>Puoi tornare alla riparazione per inserirlo, oppure " +
            "<strong>forzare il salvataggio</strong> senza telefono."
        );
    }

    function promptSenzaTelefonoForce() {
        if (hasTelefonoOrCellulare()) {
            setForzaSenzaTelefono(false);
            return Promise.resolve(true);
        }
        if (isForzaSenzaTelefono()) {
            return Promise.resolve(true);
        }

        const ask =
            window.LabRepairConfirm && typeof window.LabRepairConfirm.ask === "function"
                ? window.LabRepairConfirm.ask.bind(window.LabRepairConfirm)
                : null;

        if (typeof ask !== "function") {
            setForzaSenzaTelefono(true);
            return Promise.resolve(true);
        }

        return ask({
            title: "Telefono mancante",
            message: buildSenzaTelefonoMessage(),
            confirmLabel: "Forza salvataggio",
            cancelLabel: "Inserisci telefono",
            confirmClass: "btn btn-warning",
            variant: "danger",
        }).then(function (forza) {
            if (forza) {
                setForzaSenzaTelefono(true);
                return true;
            }
            setForzaSenzaTelefono(false);
            focusTelefonoFields();
            return false;
        });
    }

    function needsSenzaTelefonoForce() {
        return !hasTelefonoOrCellulare() && !isForzaSenzaTelefono();
    }

    function getRequiredFields() {
        const fields = REQUIRED_FIELDS.slice();
        if (isPrezioso() && hasTipoMetallo()) {
            fields.splice(4, 0, PESO_REQUIRED);
        }
        if (isAssistenzaRiparatore()) {
            fields.push(CENTRO_REQUIRED);
        }
        if (isInConsegna()) {
            fields.push(PREZZO_PUBBLICO_REQUIRED);
        }
        return fields;
    }

    function todayIsoDateLocal() {
        if (typeof window.labrepairTodayIsoDate === "function") {
            return window.labrepairTodayIsoDate();
        }
        const now = new Date();
        const y = now.getFullYear();
        const m = String(now.getMonth() + 1).padStart(2, "0");
        const d = String(now.getDate()).padStart(2, "0");
        return y + "-" + m + "-" + d;
    }

    function isConsegnaNotBeforeToday(field) {
        if (!field) {
            return true;
        }
        // Solo Nuova riparazione: in modifica la data retroattiva non blocca.
        if (
            typeof window.labrepairIsNuovaRiparazioneForm === "function"
                ? !window.labrepairIsNuovaRiparazioneForm()
                : !(
                      document.getElementById("praticaForm") &&
                      document
                          .getElementById("praticaForm")
                          .getAttribute("data-pratica-nuova") === "1"
                  )
        ) {
            return true;
        }
        const value = String(field.value || "").trim();
        if (!value) {
            return true;
        }
        return value >= todayIsoDateLocal();
    }

    function isFilled(config) {
        const field = getField(config);
        if (!field && !config.inConsegnaPrezzoPubblico) {
            return true;
        }

        if (config.inConsegnaPrezzoPubblico) {
            if (!isInConsegna() || isSenzaSpesa()) {
                return true;
            }
            return parseAmount(field && field.value) > 0;
        }

        if (config.optionalIfNomeCognome && hasNomeECognome()) {
            return true;
        }

        if (config.optionalIfTelefonoOrCellulare) {
            if (isForzaSenzaTelefono()) {
                return true;
            }
            return hasTelefonoOrCellulare();
        }

        if (config.id === "id_descrizione") {
            return Boolean((field.value || "").trim());
        }

        if (config.id === "id_peso_grammi") {
            if (!isPrezioso() || !hasTipoMetallo()) {
                return true;
            }
            const raw = (field.value || "").trim().replace(",", ".");
            if (!raw) {
                return false;
            }
            const value = Number(raw);
            return Number.isFinite(value) && value > 0;
        }

        if (config.notBeforeToday) {
            if (!(field.value || "").trim()) {
                const wrap = field.closest(".st-date-field");
                const text = wrap ? wrap.querySelector(".st-date-text") : null;
                if (text && String(text.value || "").trim()) {
                    if (typeof window.labrepairCommitDateFields === "function") {
                        window.labrepairCommitDateFields(wrap);
                    }
                }
            }
            if (!(field.value || "").trim()) {
                return false;
            }
            return isConsegnaNotBeforeToday(field);
        }

        return Boolean((field.value || "").trim());
    }

    function focusField(config) {
        let target = getFocusTarget(config);

        if (config.inConsegnaPrezzoPubblico) {
            const senzaSpesa = document.getElementById("id_senza_spesa");
            const prezzoAl = document.getElementById("id_prezzo_al");
            target = prezzoAl || senzaSpesa || target;
        }

        if (
            config.optionalIfNomeCognome &&
            !isFilled(config) &&
            !hasNomeECognome()
        ) {
            const cognome = document.getElementById("id_referente_cognome");
            const nome = document.getElementById("id_referente_nome");
            if (cognome && !(cognome.value || "").trim()) {
                target = cognome;
            } else if (nome && !(nome.value || "").trim()) {
                target = nome;
            }
        }

        if (config.optionalIfTelefonoOrCellulare && !hasTelefonoOrCellulare()) {
            if (!fieldTrimmedValue("id_referente_telefono")) {
                target = document.getElementById("id_referente_telefono") || target;
            } else {
                target = document.getElementById("id_referente_cellulare") || target;
            }
        }

        if (!target) {
            return;
        }

        const importiDettaglio = document.getElementById("praticaImportiDettaglio");
        if (
            importiDettaglio &&
            importiDettaglio.hidden &&
            importiDettaglio.contains(target) &&
            typeof window.labrepairRevealImportiDettaglio === "function"
        ) {
            window.labrepairRevealImportiDettaglio();
        }

        target.focus({ preventScroll: true });
        if (!window.labrepairSuppressFieldBlurUi) {
            target.scrollIntoView({ behavior: "auto", block: "center" });
        }
    }

    function findFirstMissing() {
        const requiredFields = getRequiredFields();
        for (let index = 0; index < requiredFields.length; index += 1) {
            const config = requiredFields[index];
            if (!isFilled(config)) {
                return config;
            }
        }
        return null;
    }

    function findFirstServerError() {
        const requiredFields = getRequiredFields();
        for (let index = 0; index < requiredFields.length; index += 1) {
            const config = requiredFields[index];
            const field = getField(config);
            if (!field) {
                continue;
            }

            const wrapper = field.closest(".mb-3, .st-cliente-search-field");
            if (wrapper && wrapper.querySelector(".invalid-feedback")) {
                return config;
            }
        }
        return null;
    }

    function clearClientFieldErrors(scope) {
        const root = scope || document.getElementById("praticaForm") || document;
        root.querySelectorAll("[data-pratica-client-error]").forEach(function (el) {
            el.remove();
        });
        root.querySelectorAll(".is-invalid[data-pratica-client-invalid]").forEach(
            function (el) {
                el.classList.remove("is-invalid");
                el.removeAttribute("data-pratica-client-invalid");
                el.removeAttribute("aria-invalid");
            }
        );
    }

    function getFieldErrorContainer(target) {
        if (!target) {
            return null;
        }
        const dateWrap = target.closest(".st-date-field");
        if (dateWrap) {
            return dateWrap.parentElement || dateWrap;
        }
        return (
            target.closest(".mb-3, .st-cliente-search-field, .st-anagrafica-fact") ||
            target.parentElement
        );
    }

    function showInlineFieldError(target, message) {
        if (!target || !message) {
            return;
        }
        clearClientFieldErrors();

        const markInvalid = function (el) {
            if (!el) {
                return;
            }
            el.classList.add("is-invalid");
            el.setAttribute("data-pratica-client-invalid", "1");
            el.setAttribute("aria-invalid", "true");
        };

        markInvalid(target);
        const dateWrap = target.closest(".st-date-field");
        if (dateWrap) {
            const text = dateWrap.querySelector(".st-date-text");
            const native = dateWrap.querySelector(".st-date-native");
            markInvalid(text);
            markInvalid(native);
        }

        const container = getFieldErrorContainer(target);
        if (!container) {
            return;
        }

        const feedback = document.createElement("div");
        feedback.className = "invalid-feedback d-block";
        feedback.setAttribute("data-pratica-client-error", "1");
        feedback.setAttribute("role", "alert");
        feedback.textContent = message;
        container.appendChild(feedback);

        function clearOnEdit() {
            clearClientFieldErrors();
            target.removeEventListener("input", clearOnEdit);
            target.removeEventListener("change", clearOnEdit);
            if (dateWrap) {
                const text = dateWrap.querySelector(".st-date-text");
                const native = dateWrap.querySelector(".st-date-native");
                if (text) {
                    text.removeEventListener("input", clearOnEdit);
                    text.removeEventListener("change", clearOnEdit);
                }
                if (native) {
                    native.removeEventListener("input", clearOnEdit);
                    native.removeEventListener("change", clearOnEdit);
                }
            }
        }

        target.addEventListener("input", clearOnEdit);
        target.addEventListener("change", clearOnEdit);
        if (dateWrap) {
            const text = dateWrap.querySelector(".st-date-text");
            const native = dateWrap.querySelector(".st-date-native");
            if (text) {
                text.addEventListener("input", clearOnEdit);
                text.addEventListener("change", clearOnEdit);
            }
            if (native) {
                native.addEventListener("input", clearOnEdit);
                native.addEventListener("change", clearOnEdit);
            }
        }
    }

    function showFieldMessage(config) {
        focusField(config);
        let target = getFocusTarget(config);

        if (config.inConsegnaPrezzoPubblico) {
            const senzaSpesa = document.getElementById("id_senza_spesa");
            const prezzoAl = document.getElementById("id_prezzo_al");
            target = prezzoAl || senzaSpesa || target;
        }

        if (
            config.optionalIfTelefonoOrCellulare &&
            !hasTelefonoOrCellulare()
        ) {
            if (!fieldTrimmedValue("id_referente_telefono")) {
                target = document.getElementById("id_referente_telefono") || target;
            } else {
                target = document.getElementById("id_referente_cellulare") || target;
            }
        }

        if (!target) {
            return;
        }

        let message = config.message;
        if (config.notBeforeToday) {
            const field = getField(config);
            const dateTarget = field || target;
            if (
                dateTarget &&
                dateTarget.value &&
                !isConsegnaNotBeforeToday(dateTarget) &&
                config.notBeforeTodayMessage
            ) {
                message = config.notBeforeTodayMessage;
            }
        }

        showInlineFieldError(target, message);
    }

    /**
     * Stessa validazione usata da Salva e da Stampa Busta/Privacy.
     * @returns {{ok: boolean, message?: string, reason?: string}}
     */
    window.labrepairValidatePraticaForm = function () {
        const form = document.getElementById("praticaForm");
        if (form && typeof window.labrepairSyncNoAutofillMirrors === "function") {
            window.labrepairSyncNoAutofillMirrors(form);
        }
        if (typeof window.labrepairCommitDateFields === "function") {
            if (!window.labrepairCommitDateFields(form || document)) {
                const invalidDate = (form || document).querySelector(
                    ".st-date-text:invalid, .st-date-text[aria-invalid='true']"
                );
                let dateHint = "Controlla le date inserite (formato gg/mm/aa).";
                if (invalidDate && invalidDate.validationMessage) {
                    dateHint = invalidDate.validationMessage;
                }
                if (invalidDate) {
                    showInlineFieldError(invalidDate, dateHint);
                    try {
                        invalidDate.focus({ preventScroll: true });
                        if (!window.labrepairSuppressFieldBlurUi) {
                            invalidDate.scrollIntoView({
                                behavior: "auto",
                                block: "center",
                            });
                        }
                    } catch (error) {
                        // ignore
                    }
                }
                return {
                    ok: false,
                    reason: "date",
                    message: dateHint,
                };
            }
        }

        const senzaSpesa = document.getElementById("id_senza_spesa");
        if (senzaSpesa && typeof senzaSpesa.setCustomValidity === "function") {
            senzaSpesa.setCustomValidity("");
        }
        clearTelefonoCellulareValidity();

        const missing = findFirstMissing();
        if (!missing) {
            return { ok: true };
        }
        if (missing.optionalIfTelefonoOrCellulare) {
            return {
                ok: false,
                reason: "telefono",
                message:
                    "Impossibile salvare la scheda: inserisci il telefono o il cellulare, oppure conferma «Forza salvataggio».",
            };
        }
        showFieldMessage(missing);
        let detail = missing.message;
        if (missing.notBeforeToday) {
            const field = getField(missing);
            if (field && field.value && !isConsegnaNotBeforeToday(field)) {
                detail = missing.notBeforeTodayMessage || detail;
            }
        }
        return {
            ok: false,
            reason: missing.id || "required",
            message: detail,
        };
    };

    window.labrepairShowSaveBlockReason = function (message, options) {
        options = options || {};
        const form = document.getElementById("praticaForm");
        const existing = document.getElementById("praticaSaveClientAlert");
        if (existing) {
            existing.remove();
        }
        if (!message) {
            return;
        }

        // Preferisci messaggi accanto al campo; l'alert in alto solo se richiesto.
        if (!options.forceTop && options.target) {
            showInlineFieldError(options.target, String(message).replace(
                /^Impossibile salvare la scheda:\s*/i,
                ""
            ));
            return;
        }
        if (!options.forceTop) {
            return;
        }
        if (!form) {
            return;
        }
        const detail = String(message).replace(
            /^Impossibile salvare la scheda:\s*/i,
            ""
        );
        const alert = document.createElement("div");
        alert.id = "praticaSaveClientAlert";
        alert.className = "alert alert-danger";
        alert.setAttribute("role", "alert");
        alert.textContent = detail;
        form.parentNode.insertBefore(alert, form);
    };

    function initPraticaRequiredOrder() {
        const form = document.getElementById("praticaForm");
        if (!form) {
            return;
        }

        form.addEventListener(
            "submit",
            function (event) {
                if (needsSenzaTelefonoForce()) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    promptSenzaTelefonoForce().then(function (forza) {
                        if (forza) {
                            if (typeof form.requestSubmit === "function") {
                                form.requestSubmit();
                            } else {
                                form.submit();
                            }
                        }
                    });
                    return;
                }

                const result = window.labrepairValidatePraticaForm();
                if (result.ok) {
                    return;
                }
                event.preventDefault();
                event.stopImmediatePropagation();
                if (result.reason === "telefono") {
                    promptSenzaTelefonoForce().then(function (forza) {
                        if (forza) {
                            if (typeof form.requestSubmit === "function") {
                                form.requestSubmit();
                            } else {
                                form.submit();
                            }
                        }
                    });
                    return;
                }
                // Messaggio già mostrato accanto al campo in labrepairValidatePraticaForm.
            },
            true
        );

        ["id_referente_telefono", "id_referente_cellulare"].forEach(function (id) {
            const field = document.getElementById(id);
            if (!field) {
                return;
            }
            field.addEventListener("input", function () {
                if (hasTelefonoOrCellulare()) {
                    setForzaSenzaTelefono(false);
                }
            });
            field.addEventListener("change", function () {
                if (hasTelefonoOrCellulare()) {
                    setForzaSenzaTelefono(false);
                }
            });
        });

        // Validazione HTML5 nativa (campi required del browser).
        form.addEventListener(
            "invalid",
            function (event) {
                event.preventDefault();
                const target = event.target;
                const detail =
                    (target && target.validationMessage) ||
                    "Valore non valido.";
                if (target) {
                    showInlineFieldError(target, detail);
                    try {
                        target.focus({ preventScroll: true });
                        if (!window.labrepairSuppressFieldBlurUi) {
                            target.scrollIntoView({
                                behavior: "auto",
                                block: "center",
                            });
                        }
                    } catch (error) {
                        // ignore
                    }
                }
            },
            true
        );

        const serverError = findFirstServerError();
        if (serverError) {
            focusField(serverError);
        }
    }

    window.labrepairNeedsSenzaTelefonoForce = needsSenzaTelefonoForce;
    window.labrepairPromptSenzaTelefonoForce = promptSenzaTelefonoForce;

    document.addEventListener("DOMContentLoaded", initPraticaRequiredOrder);
})();
