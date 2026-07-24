(function () {
    function todayIsoDate() {
        const now = new Date();
        const pad = function (value) {
            return String(value).padStart(2, "0");
        };
        return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    }

    function getOptionLabel(select, value) {
        const option = Array.from(select.options).find(function (item) {
            return item.value === value;
        });
        return option ? option.text.trim() : value;
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function initPraticaStatoChange() {
        const statoField = document.getElementById("id_stato");
        const dataRiparatoreField = document.getElementById("id_data_riparatore");
        const dataRientroField = document.getElementById("id_data_rientro");

        if (!statoField) {
            return;
        }

        let previousStato = statoField.value;
        let isHandling = false;

        statoField.addEventListener("change", function () {
            if (isHandling) {
                return;
            }

            const newStato = statoField.value;
            if (newStato === previousStato) {
                return;
            }

            const oldLabel = getOptionLabel(statoField, previousStato);
            const newLabel = getOptionLabel(statoField, newStato);
            const pendingStato = newStato;

            const confirmPromise = window.LabRepairConfirm
                ? window.LabRepairConfirm.ask({
                    title: "Conferma cambio stato",
                    message:
                        'Vuoi passare da <span class="st-confirm-name">' + escapeHtml(oldLabel) +
                        '</span> a <span class="st-confirm-name">' + escapeHtml(newLabel) + "</span>?",
                    confirmLabel: "Conferma",
                    cancelLabel: "Annulla",
                    variant: "info",
                })
                : Promise.resolve(window.confirm(
                    'Confermi il cambio di stato da "' + oldLabel + '" a "' + newLabel + '"?'
                ));

            confirmPromise.then(function (confirmed) {
                if (!confirmed) {
                    isHandling = true;
                    statoField.value = previousStato;
                    isHandling = false;
                    return;
                }

                const today = todayIsoDate();

                if (pendingStato === "riparatore" && dataRiparatoreField) {
                    dataRiparatoreField.value = today;
                }

                if (pendingStato === "in_consegna" && dataRientroField) {
                    dataRientroField.value = today;
                }

                previousStato = pendingStato;
            });
        });
    }

    document.addEventListener("DOMContentLoaded", initPraticaStatoChange);
})();
