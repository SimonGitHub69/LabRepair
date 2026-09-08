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

    function setImportiDettaglioVisible(visible) {
        const detail = document.getElementById("praticaImportiDettaglio");
        const toggle = document.querySelector("[data-importi-dettaglio-toggle]");
        if (!detail || !toggle) {
            return;
        }

        detail.hidden = !visible;
        toggle.setAttribute("aria-expanded", visible ? "true" : "false");
        toggle.title = visible ? "Nascondi dettaglio costi" : "Mostra dettaglio costi";
        toggle.classList.toggle("is-active", visible);

        const icon = toggle.querySelector("[data-importi-dettaglio-icon]");
        if (icon) {
            icon.classList.toggle("ti-eye", !visible);
            icon.classList.toggle("ti-eye-off", visible);
        }
    }

    window.labrepairRevealImportiDettaglio = function () {
        setImportiDettaglioVisible(true);
    };

    function detailHasVisibleErrors(detail) {
        if (!detail) {
            return false;
        }
        return !!detail.querySelector(
            ".invalid-feedback.d-block, .is-invalid, .form-control.is-invalid"
        );
    }

    function initImportiDettaglioToggle() {
        const detail = document.getElementById("praticaImportiDettaglio");
        const toggle = document.querySelector("[data-importi-dettaglio-toggle]");
        if (!detail || !toggle) {
            return;
        }

        // Di default nascosto; apri solo se ci sono errori server sul dettaglio.
        setImportiDettaglioVisible(detailHasVisibleErrors(detail));

        toggle.addEventListener("click", function () {
            setImportiDettaglioVisible(detail.hidden);
        });
    }

    function bindSelectOnFocus(field) {
        if (!field || field.dataset.selectOnFocusBound === "1") {
            return;
        }
        field.dataset.selectOnFocusBound = "1";

        field.addEventListener("focus", function () {
            // Seleziona tutto al focus: digitando sostituisci il valore (es. 50,00 → 5).
            const el = field;
            requestAnimationFrame(function () {
                try {
                    el.select();
                } catch (error) {
                    // ignore
                }
            });
            // Chrome/Edge annullano la selezione al mouseup dopo click-focus.
            function onMouseUp(event) {
                event.preventDefault();
                el.removeEventListener("mouseup", onMouseUp);
            }
            el.addEventListener("mouseup", onMouseUp);
        });
    }

    function initSelectOnFocusAmountFields() {
        [
            "id_peso_grammi",
            "id_costo_lavorazione",
            "id_costo_materiale",
            "id_oro_aggiunto",
            "id_prezzo_unita",
            "id_prezzo_al",
            "id_prezzo_pagato",
        ].forEach(function (id) {
            bindSelectOnFocus(document.getElementById(id));
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
        initImportiDettaglioToggle();
        initSelectOnFocusAmountFields();

        if (tipoOggettoField) {
            tipoOggettoField.addEventListener("change", updatePrezzoUnitaLabel);
            updatePrezzoUnitaLabel();
        }
    }

    document.addEventListener("DOMContentLoaded", initPraticaImporti);
})();
