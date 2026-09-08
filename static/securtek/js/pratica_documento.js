(function () {
    let lastAnagrafica = null;
    let lastNotifiedClienteId = null;
    let forceShowDocumento = false;
    let notifyInFlight = false;

    function getCsrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (match) {
            return decodeURIComponent(match[1]);
        }
        const input = document.querySelector("[name=csrfmiddlewaretoken]");
        return input ? input.value : "";
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function isTipologiaPrezioso() {
        const field = document.getElementById("id_tipologia");
        return !!(field && field.value === "prezioso");
    }

    function getPanel() {
        return document.querySelector("[data-cliente-documento-panel]");
    }

    function getField(name) {
        return document.getElementById("id_doc_" + name);
    }

    function syncAnagraficaCompletaVisibility() {
        const wrap = document.getElementById("clienteAnagraficaCompleta");
        if (!wrap) {
            return;
        }
        wrap.hidden = !(isTipologiaPrezioso() || forceShowDocumento);
    }

    function setEnabled(enabled) {
        const panel = getPanel();
        if (!panel) {
            return;
        }
        panel.querySelectorAll("input, button").forEach(function (el) {
            el.disabled = !enabled;
        });
    }

    function setAlert(message, variant) {
        const panel = getPanel();
        if (!panel) {
            return;
        }
        const alert = panel.querySelector("[data-documento-alert]");
        if (!alert) {
            return;
        }
        if (!message) {
            alert.hidden = true;
            alert.textContent = "";
            alert.classList.remove("alert-danger", "alert-success", "alert-warning");
            return;
        }
        alert.hidden = false;
        alert.textContent = message;
        alert.classList.remove("alert-danger", "alert-success", "alert-warning");
        if (variant === "success") {
            alert.classList.add("alert-success");
        } else if (variant === "warning") {
            alert.classList.add("alert-warning");
        } else {
            alert.classList.add("alert-danger");
        }
    }

    function updateBadge(anagrafica) {
        const panel = getPanel();
        if (!panel) {
            return;
        }
        const badge = panel.querySelector("[data-documento-badge]");
        const card = panel.querySelector(".st-cliente-documento-card");
        if (!badge) {
            return;
        }

        const hasScadenza = !!(anagrafica && anagrafica.documento_data_scadenza_iso);
        const scaduto = !!(anagrafica && anagrafica.documento_scaduto);

        if (!anagrafica || !hasScadenza) {
            badge.hidden = true;
            if (card) {
                card.classList.remove("is-warning");
            }
            return;
        }

        badge.hidden = false;
        if (scaduto) {
            badge.className = "badge bg-red-lt";
            badge.textContent = "Scaduto";
            if (card) {
                card.classList.add("is-warning");
            }
        } else {
            badge.className = "badge bg-green-lt";
            badge.textContent = "Valido";
            if (card) {
                card.classList.remove("is-warning");
            }
        }
    }

    function setStampaPrivacy(value) {
        const panel = getPanel();
        if (!panel) {
            return;
        }
        const yes = value === true || value === "True" || value === "true" || value === 1;
        panel.querySelectorAll('input[name="stampa_privacy"]').forEach(function (radio) {
            radio.checked = yes ? radio.value === "True" : radio.value === "False";
        });
    }

    function focusDocumentoPanel() {
        const panel = getPanel();
        if (!panel) {
            return;
        }
        panel.scrollIntoView({ behavior: "smooth", block: "center" });
        const first = getField("documento_tipo");
        if (first) {
            window.setTimeout(function () {
                first.focus();
            }, 250);
        }
    }

    function applyScadutoAlert(anagrafica) {
        if (!anagrafica || !anagrafica.documento_scaduto) {
            return;
        }
        if (isTipologiaPrezioso()) {
            setAlert(
                "Documento scaduto: obbligatorio aggiornarlo e premere «Salva documento» prima di salvare la riparazione preziosa.",
                "danger"
            );
        } else {
            setAlert(
                "Documento scaduto: puoi aggiornarlo ora oppure lasciarlo invariato.",
                "warning"
            );
        }
    }

    function notifyDocumentoScaduto(anagrafica, options) {
        options = options || {};
        if (!anagrafica || !anagrafica.documento_scaduto) {
            return;
        }

        const clienteId = anagrafica.id;
        if (!options.force && lastNotifiedClienteId === clienteId) {
            applyScadutoAlert(anagrafica);
            return;
        }
        if (notifyInFlight) {
            return;
        }

        lastNotifiedClienteId = clienteId;
        const nome = anagrafica.display_name || "il cliente";
        const scadenza = anagrafica.documento_data_scadenza || "";
        const prezioso = isTipologiaPrezioso();

        let message =
            "Il documento di identità di <strong>" +
            escapeHtml(nome) +
            "</strong>";
        if (scadenza) {
            message +=
                " è scaduto il <strong>" + escapeHtml(scadenza) + "</strong>.";
        } else {
            message += " risulta scaduto.";
        }
        message +=
            "<br><br>Vuoi aggiornare i dati sull'anagrafica adesso, oppure lasciare il documento invariato?";
        if (prezioso) {
            message +=
                "<br><br><em>Con oggetti preziosi l'aggiornamento è obbligatorio per salvare la riparazione.</em>";
        }

        const ask = window.labrepairConfirm;
        if (typeof ask !== "function") {
            forceShowDocumento = true;
            syncAnagraficaCompletaVisibility();
            applyScadutoAlert(anagrafica);
            return;
        }

        notifyInFlight = true;
        ask({
            title: "Documento scaduto",
            message: message,
            confirmLabel: "Aggiorna documento",
            cancelLabel: "Lascia invariato",
            confirmClass: prezioso ? "btn btn-danger" : "btn btn-primary",
            variant: prezioso ? "danger" : "info",
        })
            .then(function (aggiorna) {
                if (aggiorna) {
                    forceShowDocumento = true;
                    syncAnagraficaCompletaVisibility();
                    applyScadutoAlert(anagrafica);
                    focusDocumentoPanel();
                    return;
                }

                // Lascia invariato: bloccante solo se prezioso.
                if (prezioso) {
                    forceShowDocumento = false;
                    syncAnagraficaCompletaVisibility();
                    applyScadutoAlert(anagrafica);
                } else {
                    forceShowDocumento = false;
                    syncAnagraficaCompletaVisibility();
                    setAlert("");
                }
            })
            .finally(function () {
                notifyInFlight = false;
            });
    }

    function fillDocumentoFields(anagrafica, options) {
        options = options || {};
        const panel = getPanel();
        if (!panel) {
            return;
        }

        if (!anagrafica) {
            clearDocumentoFields();
            return;
        }

        lastAnagrafica = anagrafica;

        const tipo = getField("documento_tipo");
        const numero = getField("documento_numero");
        const rilasciato = getField("documento_rilasciato_da");
        const rilascio = getField("documento_data_rilascio");
        const scadenza = getField("documento_data_scadenza");

        if (tipo) {
            tipo.value = anagrafica.documento_tipo || "";
        }
        if (numero) {
            numero.value = anagrafica.documento_numero || "";
        }
        if (rilasciato) {
            rilasciato.value = anagrafica.documento_rilasciato_da || "";
        }
        if (rilascio) {
            rilascio.value = anagrafica.documento_data_rilascio_iso || "";
        }
        if (scadenza) {
            scadenza.value = anagrafica.documento_data_scadenza_iso || "";
        }
        setStampaPrivacy(anagrafica.stampa_privacy);

        panel.dataset.updateUrl = anagrafica.documento_update_url || "";
        setEnabled(true);
        updateBadge(anagrafica);

        if (anagrafica.documento_scaduto) {
            if (isTipologiaPrezioso()) {
                forceShowDocumento = false;
            }
            syncAnagraficaCompletaVisibility();
            if (options.skipNotify) {
                applyScadutoAlert(anagrafica);
            } else {
                notifyDocumentoScaduto(anagrafica, options);
            }
        } else {
            forceShowDocumento = forceShowDocumento && !isTipologiaPrezioso();
            syncAnagraficaCompletaVisibility();
            setAlert("");
        }
    }

    function clearDocumentoFields() {
        const panel = getPanel();
        if (!panel) {
            return;
        }

        lastAnagrafica = null;
        lastNotifiedClienteId = null;
        forceShowDocumento = false;

        [
            "documento_tipo",
            "documento_numero",
            "documento_rilasciato_da",
            "documento_data_rilascio",
            "documento_data_scadenza",
        ].forEach(function (name) {
            const field = getField(name);
            if (field) {
                field.value = "";
            }
        });
        setStampaPrivacy(false);
        panel.dataset.updateUrl = "";
        setEnabled(false);
        updateBadge(null);
        setAlert("");
        syncAnagraficaCompletaVisibility();
    }

    function collectFormData() {
        const formData = new FormData();
        const fields = [
            "documento_tipo",
            "documento_numero",
            "documento_rilasciato_da",
            "documento_data_rilascio",
            "documento_data_scadenza",
        ];
        fields.forEach(function (name) {
            const field = getField(name);
            formData.append(name, field ? field.value : "");
        });

        const privacy = document.querySelector(
            '[data-cliente-documento-panel] input[name="stampa_privacy"]:checked'
        );
        formData.append("stampa_privacy", privacy ? privacy.value : "False");
        return formData;
    }

    function saveDocumento() {
        const panel = getPanel();
        if (!panel) {
            return Promise.reject(new Error("Pannello documento non trovato."));
        }
        const url = panel.dataset.updateUrl || "";
        if (!url) {
            setAlert("Seleziona un cliente prima di salvare il documento.", "danger");
            return Promise.reject(new Error("Cliente non selezionato."));
        }

        const saveBtn = panel.querySelector("[data-documento-save]");
        if (saveBtn) {
            saveBtn.disabled = true;
        }
        setAlert("");

        return fetch(url, {
            method: "POST",
            body: collectFormData(),
            credentials: "same-origin",
            headers: {
                Accept: "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": getCsrfToken(),
            },
        })
            .then(function (response) {
                return response
                    .json()
                    .catch(function () {
                        return {};
                    })
                    .then(function (payload) {
                        return { response: response, payload: payload || {} };
                    });
            })
            .then(function (result) {
                const payload = result.payload;
                if (!result.response.ok || !payload.ok) {
                    const message = payload.message || "Salvataggio documento non riuscito.";
                    setAlert(message, "danger");
                    if (payload.anagrafica) {
                        fillDocumentoFields(payload.anagrafica, { skipNotify: true });
                    } else {
                        setEnabled(true);
                    }
                    throw new Error(message);
                }
                lastNotifiedClienteId = payload.anagrafica
                    ? payload.anagrafica.id
                    : lastNotifiedClienteId;
                fillDocumentoFields(payload.anagrafica || null, { skipNotify: true });
                setAlert(payload.message || "Documento aggiornato sull'anagrafica.", "success");
                return payload;
            })
            .finally(function () {
                if (saveBtn && panel.dataset.updateUrl) {
                    saveBtn.disabled = false;
                }
            });
    }

    function onTipologiaChanged() {
        syncAnagraficaCompletaVisibility();
        if (
            lastAnagrafica &&
            lastAnagrafica.documento_scaduto &&
            isTipologiaPrezioso()
        ) {
            notifyDocumentoScaduto(lastAnagrafica, { force: true });
        } else if (lastAnagrafica && lastAnagrafica.documento_scaduto) {
            applyScadutoAlert(lastAnagrafica);
        } else {
            setAlert("");
        }
    }

    window.labrepairFillClienteDocumento = fillDocumentoFields;
    window.labrepairClearClienteDocumento = clearDocumentoFields;
    window.labrepairSaveClienteDocumento = saveDocumento;
    window.labrepairSyncAnagraficaCompletaVisibility = syncAnagraficaCompletaVisibility;
    window.labrepairOnTipologiaDocumentoCheck = onTipologiaChanged;

    document.addEventListener("DOMContentLoaded", function () {
        const panel = getPanel();
        if (!panel) {
            return;
        }
        const saveBtn = panel.querySelector("[data-documento-save]");
        if (saveBtn) {
            saveBtn.addEventListener("click", function () {
                saveDocumento().catch(function () {
                    return null;
                });
            });
        }
        syncAnagraficaCompletaVisibility();
    });
})();
