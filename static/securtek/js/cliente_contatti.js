(function () {
    const openBtn = document.getElementById("modificaClienteContatti");
    const modal = document.getElementById("clienteContattiModal");
    const form = document.getElementById("clienteContattiForm");
    if (!openBtn || !modal || !form) {
        return;
    }

    const urlTemplate = modal.dataset.urlTemplate || "";
    const praticaId = modal.dataset.praticaId || "";
    const alertBox = document.getElementById("clienteContattiAlert");
    const nameNode = document.getElementById("clienteContattiName");
    const saveBtn = form.querySelector("[data-cliente-contatti-save]");

    function getCsrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (match) {
            return decodeURIComponent(match[1]);
        }
        const input = document.querySelector("#praticaForm [name=csrfmiddlewaretoken]");
        return input ? input.value : "";
    }

    function clienteId() {
        const field = document.getElementById("id_cliente");
        return field ? String(field.value || "").trim() : "";
    }

    function clienteLabel() {
        const search = document.getElementById("clienteSearchInput");
        const fromSearch = search ? (search.dataset.selectedLabel || search.value || "") : "";
        if (String(fromSearch).trim()) {
            return String(fromSearch).trim();
        }
        const cognome = document.getElementById("id_referente_cognome");
        const nome = document.getElementById("id_referente_nome");
        return [cognome && cognome.value, nome && nome.value]
            .map(function (value) { return String(value || "").trim(); })
            .filter(Boolean)
            .join(" ");
    }

    function syncButton() {
        openBtn.hidden = !clienteId();
    }

    function fieldValue(id) {
        const element = document.getElementById(id);
        return element ? element.value || "" : "";
    }

    function setContactField(id, value) {
        const next = value || "";
        const mirror = document.getElementById(id);
        const store = document.getElementById(id + "_store");
        if (mirror) {
            mirror.value = next;
        }
        if (store) {
            store.value = next;
        }
    }

    function setAnagraficaField(name, value) {
        const node = document.querySelector('[data-anagrafica-field="' + name + '"]');
        if (node) {
            node.textContent = value && String(value).trim() ? value : "-";
        }
    }

    function setAlert(message) {
        if (!alertBox) {
            return;
        }
        alertBox.textContent = message || "";
        alertBox.hidden = !message;
    }

    function openModal() {
        if (!clienteId()) {
            return;
        }
        const telefono = document.getElementById("clienteContattiTelefono");
        const cellulare = document.getElementById("clienteContattiCellulare");
        const email = document.getElementById("clienteContattiEmail");
        if (telefono) {
            telefono.value = fieldValue("id_referente_telefono");
        }
        if (cellulare) {
            cellulare.value = fieldValue("id_referente_cellulare");
        }
        if (email) {
            email.value = fieldValue("id_referente_email");
        }
        if (nameNode) {
            const label = clienteLabel();
            nameNode.textContent = label ? label + ". " : "";
        }
        setAlert("");
        modal.hidden = false;
        document.body.classList.add("st-confirm-open");
        if (telefono) {
            telefono.focus();
            telefono.select();
        }
    }

    function closeModal() {
        modal.hidden = true;
        const confirmModal = document.getElementById("stConfirmModal");
        if (!confirmModal || confirmModal.hidden) {
            document.body.classList.remove("st-confirm-open");
        }
    }

    function applySaved(payload) {
        setContactField("id_referente_telefono", payload.telefono);
        setContactField("id_referente_cellulare", payload.cellulare);
        setContactField("id_referente_email", payload.email);
        setAnagraficaField("telefono", payload.telefono);
        setAnagraficaField("cellulare", payload.cellulare);
        setAnagraficaField("email", payload.email);
        const praticaForm = document.getElementById("praticaForm");
        if (praticaForm && typeof window.labrepairSyncNoAutofillMirrors === "function") {
            window.labrepairSyncNoAutofillMirrors(praticaForm);
        }
    }

    function saveContatti() {
        const id = clienteId();
        if (!id || !urlTemplate) {
            setAlert("Seleziona un cliente prima di modificare i recapiti.");
            return;
        }

        const body = new FormData(form);
        if (praticaId) {
            body.set("pratica", praticaId);
        }
        if (saveBtn) {
            saveBtn.disabled = true;
        }
        setAlert("");

        fetch(urlTemplate.replace("/0/", "/" + id + "/"), {
            method: "POST",
            body: body,
            credentials: "same-origin",
            headers: {
                Accept: "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": getCsrfToken(),
            },
        })
            .then(function (response) {
                return response.json().catch(function () {
                    return {};
                }).then(function (payload) {
                    return { response: response, payload: payload || {} };
                });
            })
            .then(function (result) {
                const payload = result.payload;
                if (!result.response.ok || !payload.ok) {
                    setAlert(payload.message || "Salvataggio recapiti non riuscito.");
                    return;
                }
                applySaved(payload);
                closeModal();
            })
            .catch(function () {
                setAlert("Salvataggio recapiti non riuscito.");
            })
            .finally(function () {
                if (saveBtn) {
                    saveBtn.disabled = false;
                }
            });
    }

    openBtn.addEventListener("click", openModal);
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        saveContatti();
    });
    const cancelBtn = form.querySelector("[data-cliente-contatti-cancel]");
    if (cancelBtn) {
        cancelBtn.addEventListener("click", closeModal);
    }
    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modal.hidden) {
            event.preventDefault();
            closeModal();
        }
    });
    document.addEventListener("labrepair:cliente-changed", syncButton);
    syncButton();
})();
