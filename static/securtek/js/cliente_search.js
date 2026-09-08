function initClienteSearch(root) {
    if (!root || root.dataset.clienteSearchReady === "1") {
        return;
    }

    const hiddenField = root.querySelector('input[type="hidden"][name="cliente"]');
    const searchInput = root.querySelector("[data-cliente-search-input]");
    const resultsBox = root.querySelector("[data-cliente-search-results]");
    const clearButton = root.querySelector("[data-cliente-search-clear]");
    const searchUrl = root.dataset.searchUrl;
    const referenteUrlTemplate = root.dataset.referenteUrlTemplate || "";

    if (!hiddenField || !searchInput || !resultsBox || !searchUrl) {
        return;
    }

    function getReferenteFields() {
        return {
            cognome: document.getElementById("id_referente_cognome"),
            nome: document.getElementById("id_referente_nome"),
            telefono: document.getElementById("id_referente_telefono"),
            cellulare: document.getElementById("id_referente_cellulare"),
            email: document.getElementById("id_referente_email"),
        };
    }

    function fillReferenteFields(data) {
        const fields = getReferenteFields();

        if (fields.cognome) {
            fields.cognome.value = data.cognome || "";
        }
        if (fields.nome) {
            fields.nome.value = data.nome || "";
        }
        if (fields.telefono) {
            fields.telefono.value = data.telefono || "";
        }
        if (fields.cellulare) {
            fields.cellulare.value = data.cellulare || "";
        }
        if (fields.email) {
            fields.email.value = data.email || "";
        }

        if (window.LabRepairNameCase && typeof window.LabRepairNameCase.formatFields === "function") {
            window.LabRepairNameCase.formatFields(fields.cognome, fields.nome);
        }

        if (typeof window.labrepairSyncNoAutofillMirrors === "function") {
            const form = document.getElementById("praticaForm");
            window.labrepairSyncNoAutofillMirrors(form);
        }
    }

    function clearReferenteFields() {
        fillReferenteFields({});
    }

    function getAnagraficaPanelNodes() {
        return {
            empty: document.getElementById("clienteAnagraficaEmpty"),
            content: document.getElementById("clienteAnagraficaContent"),
            editLink: document.getElementById("clienteAnagraficaEditLink"),
        };
    }

    function setAnagraficaField(name, value) {
        const node = document.querySelector(`[data-anagrafica-field="${name}"]`);
        if (node) {
            node.textContent = value && String(value).trim() ? value : "-";
        }
    }

    function fillAnagraficaPanel(anagrafica) {
        const nodes = getAnagraficaPanelNodes();
        if (!nodes.content) {
            return;
        }

        if (!anagrafica) {
            clearAnagraficaPanel();
            return;
        }

        [
            "display_name",
            "codice_fiscale",
            "sesso",
            "data_nascita",
            "luogo_nascita",
            "provincia_nascita",
            "telefono",
            "cellulare",
            "email",
            "residenza",
        ].forEach(function (field) {
            setAnagraficaField(field, anagrafica[field] || "");
        });

        if (typeof window.labrepairFillClienteDocumento === "function") {
            window.labrepairFillClienteDocumento(anagrafica);
        }

        if (nodes.empty) {
            nodes.empty.hidden = true;
        }
        nodes.content.hidden = false;

        if (nodes.editLink) {
            if (anagrafica.edit_url) {
                nodes.editLink.href = anagrafica.edit_url;
                nodes.editLink.hidden = false;
            } else {
                nodes.editLink.hidden = true;
            }
        }
    }

    function clearAnagraficaPanel() {
        const nodes = getAnagraficaPanelNodes();
        if (!nodes.content) {
            return;
        }

        nodes.content.querySelectorAll("[data-anagrafica-field]").forEach(function (node) {
            node.textContent = "-";
        });
        if (typeof window.labrepairClearClienteDocumento === "function") {
            window.labrepairClearClienteDocumento();
        }
        if (nodes.empty) {
            nodes.empty.hidden = false;
        }
        nodes.content.hidden = true;
        if (nodes.editLink) {
            nodes.editLink.hidden = true;
            nodes.editLink.href = "#";
        }
    }

    function fetchReferente(clienteId) {
        if (!referenteUrlTemplate || !clienteId) {
            return Promise.resolve();
        }

        const url = referenteUrlTemplate.replace("__CLIENTE_ID__", clienteId);

        return fetch(url, {
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("referente failed");
                }
                return response.json();
            })
            .then(function (data) {
                fillReferenteFields(data);
                fillAnagraficaPanel(data.anagrafica || null);
            })
            .catch(function () {
                return null;
            });
    }

    root.dataset.clienteSearchReady = "1";

    let debounceTimer = null;
    let activeRequest = null;

    function toggleClearButton() {
        if (!clearButton) {
            return;
        }
        clearButton.hidden = !hiddenField.value;
    }

    function closeResults() {
        resultsBox.hidden = true;
        resultsBox.innerHTML = "";
    }

    function renderMessage(message) {
        resultsBox.innerHTML = `<div class="st-cliente-search-empty">${message}</div>`;
        resultsBox.hidden = false;
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function renderResults(items) {
        if (!items.length) {
            renderMessage("Nessun cliente trovato.");
            return;
        }

        resultsBox.innerHTML = items.map(function (item) {
            const subtitle = item.subtitle
                ? `<span class="st-cliente-search-option-subtitle">${escapeHtml(item.subtitle)}</span>`
                : "";
            const cognome = (item.cognome || "").trim();
            const nome = (item.nome || "").trim();
            let labelHtml;
            let labelText;
            if (cognome || nome) {
                labelText = (cognome + " " + nome).trim();
                labelHtml =
                    `<span class="st-cliente-search-cognome">${escapeHtml(cognome)}</span>` +
                    (nome
                        ? ` <span class="st-cliente-search-nome">${escapeHtml(nome)}</span>`
                        : "");
            } else {
                labelText = item.label || "";
                labelHtml = escapeHtml(labelText);
            }
            return `
                <button type="button"
                        class="st-cliente-search-option"
                        data-cliente-id="${item.id}"
                        data-cliente-label="${escapeHtml(labelText)}">
                    <span class="st-cliente-search-option-label">${labelHtml}</span>
                    ${subtitle}
                </button>
            `;
        }).join("");
        resultsBox.hidden = false;
    }

    function getFilterForm() {
        return root.closest(".st-pratica-filter-card form");
    }

    function submitFilterForm() {
        const filterForm = getFilterForm();
        if (filterForm) {
            filterForm.requestSubmit();
        }
    }

    function selectCliente(id, label) {
        hiddenField.value = id;
        searchInput.value = label;
        searchInput.dataset.selectedLabel = label;
        closeResults();
        toggleClearButton();
        fetchReferente(id);
        submitFilterForm();
    }

    function clearCliente() {
        hiddenField.value = "";
        searchInput.value = "";
        delete searchInput.dataset.selectedLabel;
        closeResults();
        toggleClearButton();
        clearReferenteFields();
        clearAnagraficaPanel();
        if (getFilterForm()) {
            submitFilterForm();
            return;
        }
        searchInput.focus();
    }

    function fetchResults(params) {
        if (activeRequest) {
            activeRequest.abort();
        }

        activeRequest = new AbortController();
        const query = new URLSearchParams(params);

        return fetch(`${searchUrl}?${query.toString()}`, {
            headers: {"X-Requested-With": "XMLHttpRequest"},
            signal: activeRequest.signal,
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("search failed");
                }
                return response.json();
            })
            .then(function (data) {
                renderResults(data.results || []);
            })
            .catch(function (error) {
                if (error.name === "AbortError") {
                    return;
                }
                renderMessage("Errore durante la ricerca clienti.");
            })
            .finally(function () {
                activeRequest = null;
            });
    }

    function handleSearchInput() {
        const query = searchInput.value.trim();

        if (hiddenField.value && query !== (searchInput.dataset.selectedLabel || "")) {
            hiddenField.value = "";
            delete searchInput.dataset.selectedLabel;
            toggleClearButton();
            clearReferenteFields();
            clearAnagraficaPanel();
        }

        if (query.length < 2) {
            closeResults();
            return;
        }

        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
            fetchResults({q: query});
        }, 250);
    }

    if (hiddenField.value) {
        fetchResults({selected: hiddenField.value});
    }

    searchInput.addEventListener("input", handleSearchInput);
    searchInput.addEventListener("focus", function () {
        const query = searchInput.value.trim();
        if (query.length >= 2 && !hiddenField.value) {
            handleSearchInput();
        }
    });

    resultsBox.addEventListener("click", function (event) {
        const option = event.target.closest("[data-cliente-id]");
        if (!option) {
            return;
        }
        selectCliente(option.dataset.clienteId, option.dataset.clienteLabel);
    });

    if (clearButton) {
        clearButton.addEventListener("click", clearCliente);
    }

    document.addEventListener("click", function (event) {
        if (!root.contains(event.target)) {
            closeResults();
        }
    });

    toggleClearButton();

    const initialScript = document.getElementById("cliente-anagrafica-initial");
    if (initialScript) {
        try {
            fillAnagraficaPanel(JSON.parse(initialScript.textContent));
        } catch (error) {
            clearAnagraficaPanel();
        }
    } else if (!hiddenField.value) {
        clearAnagraficaPanel();
    }
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-cliente-search-root]").forEach(initClienteSearch);
});
