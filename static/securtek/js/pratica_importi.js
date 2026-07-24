(function () {
    function parseAmount(value) {
        const normalized = String(value || "").replace(",", ".").trim();
        const amount = Number.parseFloat(normalized);
        return Number.isFinite(amount) ? amount : 0;
    }

    function formatAmount(value) {
        return value.toFixed(2);
    }

    function readTipoOggettoUmMap() {
        const dataElement = document.getElementById("tipoOggettoUmData");
        if (!dataElement) {
            return {};
        }

        try {
            return JSON.parse(dataElement.textContent);
        } catch (error) {
            return {};
        }
    }

    function resolveUmForTipo(tipoOggettoId, umMap) {
        if (tipoOggettoId && umMap[tipoOggettoId]) {
            return umMap[tipoOggettoId];
        }
        return "gr";
    }

    function updateImportiLabels() {
        const tipoOggettoField = document.getElementById("id_tipo_oggetto");
        const prezzoLabel = document.getElementById("prezzoUnitaLabel");
        const pesoLabel = document.getElementById("pesoAggiuntoLabel");
        if (!tipoOggettoField) {
            return;
        }

        const umMap = readTipoOggettoUmMap();
        const um = resolveUmForTipo(tipoOggettoField.value, umMap);
        if (prezzoLabel) {
            prezzoLabel.textContent = `Prezzo al (${um})`;
        }
        if (pesoLabel) {
            pesoLabel.textContent = `Peso aggiunto (${um})`;
        }
    }

    function updatePrezzoUnitaLabel() {
        updateImportiLabels();
    }

    function updateCostoTotale() {
        const output = document.getElementById("costoTotaleDisplay");
        const lavorazioneField = document.getElementById("id_costo_lavorazione");
        const materialeField = document.getElementById("id_costo_materiale");
        const oroAggiuntoField = document.getElementById("id_oro_aggiunto");
        const prezzoUnitaField = document.getElementById("id_prezzo_unita");
        const senzaSpesa = document.getElementById("id_senza_spesa");

        if (!output || !lavorazioneField || !materialeField) {
            return;
        }

        const metalloAggiunto = parseAmount(oroAggiuntoField ? oroAggiuntoField.value : 0)
            * parseAmount(prezzoUnitaField ? prezzoUnitaField.value : 0);
        const total = parseAmount(lavorazioneField.value)
            + parseAmount(materialeField.value)
            + metalloAggiunto;
        output.value = formatAmount(total);

        if (senzaSpesa && typeof senzaSpesa.setCustomValidity === "function") {
            senzaSpesa.setCustomValidity("");
        }
    }

    function bindCostoTotaleField(field) {
        if (!field) {
            return;
        }

        field.addEventListener("input", updateCostoTotale);
        field.addEventListener("change", updateCostoTotale);
    }

    function bindSenzaSpesaClear() {
        const senzaSpesa = document.getElementById("id_senza_spesa");
        if (!senzaSpesa) {
            return;
        }
        senzaSpesa.addEventListener("change", function () {
            senzaSpesa.setCustomValidity("");
        });
    }

    function initPraticaImporti() {
        const tipoOggettoField = document.getElementById("id_tipo_oggetto");

        bindCostoTotaleField(document.getElementById("id_costo_lavorazione"));
        bindCostoTotaleField(document.getElementById("id_costo_materiale"));
        bindCostoTotaleField(document.getElementById("id_oro_aggiunto"));
        bindCostoTotaleField(document.getElementById("id_prezzo_unita"));
        bindSenzaSpesaClear();
        updateCostoTotale();

        if (tipoOggettoField) {
            tipoOggettoField.addEventListener("change", updatePrezzoUnitaLabel);
            updatePrezzoUnitaLabel();
        }
    }

    document.addEventListener("DOMContentLoaded", initPraticaImporti);
})();
