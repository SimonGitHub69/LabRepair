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
        },
    ];

    const PESO_REQUIRED = {
        id: "id_peso_grammi",
        message: "Inserisci il peso per gli oggetti preziosi.",
    };

    const CENTRO_REQUIRED = {
        id: "id_centro_assistenza",
        message: "Seleziona il centro assistenza.",
    };

    const COSTO_TOTALE_REQUIRED = {
        id: "costoTotaleDisplay",
        focusId: "costoTotaleDisplay",
        message:
            "Con stato «In consegna» inserisci un Costo totale oppure seleziona Senza Spesa.",
        inConsegnaCosto: true,
    };

    const PREZZO_PUBBLICO_REQUIRED = {
        id: "id_prezzo_al",
        message: "Inserisci il Prezzo al Pubblico.",
        inConsegnaPrezzoPubblico: true,
    };

    function getField(config) {
        return document.getElementById(config.id);
    }

    function getFocusTarget(config) {
        if (config.focusId) {
            return document.getElementById(config.focusId);
        }
        return getField(config);
    }

    function isPrezioso() {
        const tipologia = document.getElementById("id_tipologia");
        return Boolean(tipologia && tipologia.value === "prezioso");
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

    function getCostoTotaleValue() {
        const lavorazione = document.getElementById("id_costo_lavorazione");
        const materiale = document.getElementById("id_costo_materiale");
        const oro = document.getElementById("id_oro_aggiunto");
        const prezzoUnita = document.getElementById("id_prezzo_unita");
        const fromFields =
            parseAmount(lavorazione && lavorazione.value) +
            parseAmount(materiale && materiale.value) +
            parseAmount(oro && oro.value) * parseAmount(prezzoUnita && prezzoUnita.value);
        if (fromFields > 0) {
            return fromFields;
        }
        const display = document.getElementById("costoTotaleDisplay");
        if (display && display.value) {
            return parseAmount(display.value);
        }
        return 0;
    }

    function hasNomeECognome() {
        const nome = document.getElementById("id_referente_nome");
        const cognome = document.getElementById("id_referente_cognome");
        return Boolean(
            nome &&
                cognome &&
                (nome.value || "").trim() &&
                (cognome.value || "").trim()
        );
    }

    function hasTelefonoOrCellulare() {
        const telefono = document.getElementById("id_referente_telefono");
        const cellulare = document.getElementById("id_referente_cellulare");
        return Boolean(
            (telefono && (telefono.value || "").trim()) ||
                (cellulare && (cellulare.value || "").trim())
        );
    }

    function getRequiredFields() {
        const fields = REQUIRED_FIELDS.slice();
        if (isPrezioso()) {
            fields.splice(4, 0, PESO_REQUIRED);
        }
        if (isAssistenzaRiparatore()) {
            fields.push(CENTRO_REQUIRED);
        }
        if (isInConsegna()) {
            fields.push(COSTO_TOTALE_REQUIRED);
            fields.push(PREZZO_PUBBLICO_REQUIRED);
        }
        return fields;
    }

    function isFilled(config) {
        const field = getField(config);
        if (!field && !config.inConsegnaCosto && !config.inConsegnaPrezzoPubblico) {
            return true;
        }

        if (config.inConsegnaCosto) {
            if (!isInConsegna()) {
                return true;
            }
            if (isSenzaSpesa()) {
                return true;
            }
            return getCostoTotaleValue() > 0;
        }

        if (config.inConsegnaPrezzoPubblico) {
            if (!isInConsegna() || isSenzaSpesa()) {
                return true;
            }
            // Solo se c'è un costo totale (o stiamo ancora validando i costi)
            if (getCostoTotaleValue() <= 0) {
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
            if (!isPrezioso()) {
                return true;
            }
            const raw = (field.value || "").trim().replace(",", ".");
            if (!raw) {
                return false;
            }
            const value = Number(raw);
            return Number.isFinite(value) && value > 0;
        }

        return Boolean((field.value || "").trim());
    }

    function focusField(config) {
        let target = getFocusTarget(config);

        if (config.inConsegnaCosto) {
            const senzaSpesa = document.getElementById("id_senza_spesa");
            const costoDisplay = document.getElementById("costoTotaleDisplay");
            const lavorazione = document.getElementById("id_costo_lavorazione");
            target = senzaSpesa || lavorazione || costoDisplay || target;
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
            const telefono = document.getElementById("id_referente_telefono");
            const cellulare = document.getElementById("id_referente_cellulare");
            if (telefono && !(telefono.value || "").trim()) {
                target = telefono;
            } else if (cellulare) {
                target = cellulare;
            }
        }

        if (!target) {
            return;
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

        if (config.inConsegnaCosto) {
            const senzaSpesa = document.getElementById("id_senza_spesa");
            target = senzaSpesa || target;
        }

        if (!target || typeof target.reportValidity !== "function") {
            return;
        }

        target.setCustomValidity(config.message);

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
        const senzaSpesa = document.getElementById("id_senza_spesa");
        if (senzaSpesa && typeof senzaSpesa.setCustomValidity === "function") {
            senzaSpesa.setCustomValidity("");
        }

        const missing = findFirstMissing();
        if (!missing) {
            return { ok: true };
        }
        showFieldMessage(missing);
        return { ok: false, message: missing.message };
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
