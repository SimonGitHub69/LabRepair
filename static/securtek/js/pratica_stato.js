(function () {
    function todayIsoDate() {
        const now = new Date();
        const pad = function (value) {
            return String(value).padStart(2, "0");
        };
        return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    }

    function getStatoControls() {
        const select = document.getElementById("id_stato");
        if (select && select.tagName === "SELECT") {
            return { type: "select", root: select };
        }
        const radios = Array.from(
            document.querySelectorAll('input[type="radio"][name="stato"]')
        );
        if (radios.length) {
            return { type: "radio", root: radios };
        }
        return null;
    }

    function getStatoValue(controls) {
        if (controls.type === "select") {
            return controls.root.value;
        }
        const checked = controls.root.find(function (el) {
            return el.checked;
        });
        return checked ? checked.value : "";
    }

    function setStatoValue(controls, value) {
        if (controls.type === "select") {
            controls.root.value = value;
            return;
        }
        controls.root.forEach(function (el) {
            el.checked = el.value === value;
        });
    }

    function getStatoLabel(controls, value) {
        if (controls.type === "select") {
            const option = Array.from(controls.root.options).find(function (item) {
                return item.value === value;
            });
            return option ? option.text.trim() : value;
        }
        const match = controls.root.find(function (el) {
            return el.value === value;
        });
        if (!match) {
            return value;
        }
        const wrap = match.closest("label");
        const text = wrap
            ? wrap.querySelector(".form-check-label")
            : null;
        return text ? text.textContent.trim() : value;
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function bindChange(controls, handler) {
        if (controls.type === "select") {
            controls.root.addEventListener("change", handler);
            return;
        }
        controls.root.forEach(function (el) {
            el.addEventListener("change", handler);
        });
    }

    function initPraticaStatoChange() {
        const controls = getStatoControls();
        const dataRiparatoreField = document.getElementById("id_data_riparatore");
        const dataRientroField = document.getElementById("id_data_rientro");

        if (!controls) {
            return;
        }

        let previousStato = getStatoValue(controls);
        let isHandling = false;

        bindChange(controls, function () {
            if (isHandling) {
                return;
            }

            const newStato = getStatoValue(controls);
            if (newStato === previousStato) {
                return;
            }

            const oldLabel = getStatoLabel(controls, previousStato);
            const newLabel = getStatoLabel(controls, newStato);
            const pendingStato = newStato;

            const confirmPromise = window.LabRepairConfirm
                ? window.LabRepairConfirm.ask({
                      title: "Conferma cambio stato",
                      message:
                          'Vuoi passare da <span class="st-confirm-name">' +
                          escapeHtml(oldLabel) +
                          '</span> a <span class="st-confirm-name">' +
                          escapeHtml(newLabel) +
                          "</span>?",
                      confirmLabel: "Conferma",
                      cancelLabel: "Annulla",
                      variant: "info",
                  })
                : Promise.resolve(
                      window.confirm(
                          'Confermi il cambio di stato da "' +
                              oldLabel +
                              '" a "' +
                              newLabel +
                              '"?'
                      )
                  );

            confirmPromise.then(function (confirmed) {
                if (!confirmed) {
                    isHandling = true;
                    setStatoValue(controls, previousStato);
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
