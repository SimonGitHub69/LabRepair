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
        const statoField = document.getElementById("id_stato");
        return Boolean(statoField && statoField.value === "in_consegna");
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

    function clearTelefonoCellulareValidity() {
        ["id_referente_telefono", "id_referente_cellulare"].forEach(function (id) {
            const field = document.getElementById(id);
            if (field && typeof field.setCustomValidity === "function") {
                field.setCustomValidity("");
            }
        });
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

        target.focus({ preventScroll: false });
        target.scrollIntoView({ behavior: "smooth", block: "center" });
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

    function showFieldMessage(config) {
        focusField(config);
        let target = getFocusTarget(config);

        if (config.inConsegnaPrezzoPubblico) {
            const senzaSpesa = document.getElementById("id_senza_spesa");
            const prezzoAl = document.getElementById("id_prezzo_al");
            target = prezzoAl || senzaSpesa || target;
        }

        if (!target || typeof target.reportValidity !== "function") {
            return;
        }

        let message = config.message;
        if (
            config.notBeforeToday &&
            target.value &&
            !isConsegnaNotBeforeToday(target) &&
            config.notBeforeTodayMessage
        ) {
            message = config.notBeforeTodayMessage;
        }

        target.setCustomValidity(message);

        function clearValidity() {
            target.setCustomValidity("");
            target.removeEventListener("input", clearValidity);
            target.removeEventListener("change", clearValidity);
        }

        target.addEventListener("input", clearValidity);
        target.addEventListener("change", clearValidity);
        target.reportValidity();
    }

    /**
     * Stessa validazione usata da Salva e da Stampa Busta/Privacy.
     * @returns {{ok: boolean, message?: string}}
     */
    window.labrepairValidatePraticaForm = function () {
        const form = document.getElementById("praticaForm");
        if (form && typeof window.labrepairSyncNoAutofillMirrors === "function") {
            window.labrepairSyncNoAutofillMirrors(form);
        }
        if (typeof window.labrepairCommitDateFields === "function") {
            if (!window.labrepairCommitDateFields(form || document)) {
                return { ok: false, message: "Controlla le date inserite (gg/mm/aa)." };
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
        showFieldMessage(missing);
        let message = missing.message;
        if (missing.notBeforeToday) {
            const field = getField(missing);
            if (field && field.value && !isConsegnaNotBeforeToday(field)) {
                message = missing.notBeforeTodayMessage || message;
            }
        }
        return { ok: false, message: message };
    };

    function initPraticaRequiredOrder() {
        const form = document.getElementById("praticaForm");
        if (!form) {
            return;
        }

        form.addEventListener(
            "submit",
            function (event) {
                const result = window.labrepairValidatePraticaForm();
                if (result.ok) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
            },
            true
        );

        const serverError = findFirstServerError();
        if (serverError) {
            focusField(serverError);
        }
    }

    document.addEventListener("DOMContentLoaded", initPraticaRequiredOrder);
})();
