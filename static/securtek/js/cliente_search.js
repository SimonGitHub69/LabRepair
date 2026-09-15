function initClienteSearch(root) {
    if (!root || root.dataset.clienteSearchReady === "1") {
        return;
    }

    const hiddenField = root.querySelector('input[type="hidden"][name="cliente"]');
    const searchInput = root.querySelector("[data-cliente-search-input]");
    const resultsBox = root.querySelector("[data-cliente-search-results]");
    const clearButton = root.querySelector("[data-cliente-search-clear]");
    const searchPanel = root.querySelector("[data-cliente-search-panel]");
    const summaryBox = root.querySelector("[data-cliente-search-summary]");
    const reopenButton = root.querySelector("[data-cliente-search-reopen]");
    const canCollapse = root.dataset.clienteSearchCollapse === "1";
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
            panel: document.querySelector("[data-cliente-anagrafica-panel]"),
            collapseToggle: document.querySelector("[data-anagrafica-collapse-toggle]"),
            docBadge: document.querySelector("[data-anagrafica-doc-badge]"),
            documentoWrap: document.querySelector("[data-cliente-documento-panel]"),
        };
    }

    function setAnagraficaField(name, value) {
        const node = document.querySelector(`[data-anagrafica-field="${name}"]`);
        if (node) {
            node.textContent = value && String(value).trim() ? value : "-";
        }
    }

    function syncAnagraficaDocWarning(anagrafica) {
        const nodes = getAnagraficaPanelNodes();
        const scaduto = !!(anagrafica && anagrafica.documento_scaduto);
        if (nodes.panel) {
            nodes.panel.classList.toggle("is-warning", scaduto);
        }
        if (nodes.docBadge) {
            nodes.docBadge.hidden = !scaduto;
        }
    }

    function fillAnagraficaPanel(anagrafica, options) {
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
            window.labrepairFillClienteDocumento(anagrafica, options || {});
        }

        if (nodes.empty) {
            nodes.empty.hidden = true;
        }
        nodes.content.hidden = false;
        syncAnagraficaDocWarning(anagrafica);

        if (nodes.documentoWrap) {
            nodes.documentoWrap.hidden = false;
        }

        if (nodes.collapseToggle) {
            nodes.collapseToggle.hidden = false;
        }

        if (typeof window.labrepairSetSectionCollapsed === "function") {
            window.labrepairSetSectionCollapsed("cliente-anagrafica-body", true, false);
            window.labrepairSetSectionCollapsed("cliente-documento-body", true, false);
        }

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
        syncAnagraficaDocWarning(null);
        if (nodes.documentoWrap) {
            nodes.documentoWrap.hidden = true;
        }
        if (nodes.collapseToggle) {
            nodes.collapseToggle.hidden = true;
        }
        if (typeof window.labrepairSetSectionCollapsed === "function") {
            window.labrepairSetSectionCollapsed("cliente-anagrafica-body", false, false);
        }
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
    let activeIndex = -1;

    function toggleClearButton() {
        if (!clearButton) {
            return;
        }
        clearButton.hidden = !hiddenField.value;
    }

    function collapseSearch() {
        if (!canCollapse || !searchPanel || !summaryBox) {
            return;
        }
        searchPanel.hidden = true;
        summaryBox.hidden = false;
        closeResults();
        root.classList.add("is-cliente-selected");
    }

    function expandSearch(options) {
        if (!canCollapse || !searchPanel || !summaryBox) {
            return;
        }
        options = options || {};
        summaryBox.hidden = true;
        searchPanel.hidden = false;
        root.classList.remove("is-cliente-selected");
        if (options.clear) {
            clearCliente({ keepExpanded: true });
        } else if (options.focus !== false) {
            searchInput.focus();
            searchInput.select();
        }
    }

    function getOptions() {
        return Array.prototype.slice.call(
            resultsBox.querySelectorAll(".st-cliente-search-option[data-cliente-id]")
        );
    }

    function scrollOptionIntoList(option) {
        if (!option || resultsBox.hidden) {
            return;
        }

        const boxRect = resultsBox.getBoundingClientRect();
        const optRect = option.getBoundingClientRect();
        const borderTop = parseFloat(window.getComputedStyle(resultsBox).borderTopWidth) || 0;
        const relativeTop = optRect.top - boxRect.top - borderTop + resultsBox.scrollTop;
        const optionHeight = Math.max(option.offsetHeight, optRect.height);
        const viewHeight = resultsBox.clientHeight;
        const pad = 10;
        const maxScroll = Math.max(0, resultsBox.scrollHeight - viewHeight);

        let nextScroll = resultsBox.scrollTop;
        if (relativeTop < nextScroll + pad) {
            nextScroll = relativeTop - pad;
        } else if (relativeTop + optionHeight > nextScroll + viewHeight - pad) {
            nextScroll = relativeTop + optionHeight - viewHeight + pad;
        }

        resultsBox.scrollTop = Math.max(0, Math.min(maxScroll, nextScroll));
    }

    function setResultsOpen(isOpen) {
        root.classList.toggle("is-results-open", Boolean(isOpen));
    }

    function setActiveIndex(index) {
        const options = getOptions();
        if (!options.length) {
            activeIndex = -1;
            return;
        }

        if (index < 0) {
            index = 0;
        } else if (index >= options.length) {
            index = options.length - 1;
        }

        activeIndex = index;
        let activeOption = null;
        options.forEach(function (option, optionIndex) {
            const isActive = optionIndex === activeIndex;
            option.classList.toggle("is-active", isActive);
            option.setAttribute("aria-selected", isActive ? "true" : "false");
            if (isActive) {
                activeOption = option;
            }
        });

        if (activeOption) {
            window.requestAnimationFrame(function () {
                scrollOptionIntoList(activeOption);
                window.requestAnimationFrame(function () {
                    scrollOptionIntoList(activeOption);
                });
            });
        }
    }

    function closeResults() {
        activeIndex = -1;
        resultsBox.hidden = true;
        resultsBox.innerHTML = "";
        setResultsOpen(false);
    }

    function renderMessage(message) {
        activeIndex = -1;
        resultsBox.innerHTML = `<div class="st-cliente-search-empty">${message}</div>`;
        resultsBox.hidden = false;
        setResultsOpen(true);
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
                        role="option"
                        aria-selected="false"
                        data-cliente-id="${item.id}"
                        data-cliente-label="${escapeHtml(labelText)}">
                    <span class="st-cliente-search-option-label">${labelHtml}</span>
                    ${subtitle}
                </button>
            `;
        }).join("");
        resultsBox.hidden = false;
        resultsBox.setAttribute("role", "listbox");
        setResultsOpen(true);
        setActiveIndex(0);
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

    function focusReferenteCognome() {
        if (getFilterForm()) {
            return;
        }
        const cognome = document.getElementById("id_referente_cognome");
        if (!cognome) {
            return;
        }
        window.requestAnimationFrame(function () {
            cognome.focus();
            if (typeof cognome.select === "function") {
                cognome.select();
            }
        });
    }

    function selectCliente(id, label) {
        hiddenField.value = id;
        searchInput.value = label;
        searchInput.dataset.selectedLabel = label;
        closeResults();
        toggleClearButton();
        fetchReferente(id).finally(function () {
            collapseSearch();
            focusReferenteCognome();
        });
        submitFilterForm();
    }

    root.__labrepairSelectCliente = selectCliente;

    function clearCliente(options) {
        options = options || {};
        hiddenField.value = "";
        searchInput.value = "";
        delete searchInput.dataset.selectedLabel;
        closeResults();
        toggleClearButton();
        clearReferenteFields();
        clearAnagraficaPanel();
        if (!options.keepExpanded) {
            expandSearch({ focus: false });
        } else {
            if (searchPanel) {
                searchPanel.hidden = false;
            }
            if (summaryBox) {
                summaryBox.hidden = true;
            }
            root.classList.remove("is-cliente-selected");
        }
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

    // Cliente già selezionato: non aprire il dropdown (lista filtri / modifica scheda).
    closeResults();

    searchInput.addEventListener("input", handleSearchInput);
    searchInput.addEventListener("focus", function () {
        const query = searchInput.value.trim();
        if (query.length >= 2 && !hiddenField.value) {
            handleSearchInput();
        }
    });
    searchInput.addEventListener("keydown", function (event) {
        const options = getOptions();
        const resultsOpen = !resultsBox.hidden && options.length > 0;

        if (event.key === "ArrowDown") {
            if (!resultsOpen) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            setActiveIndex(activeIndex < 0 ? 0 : activeIndex + 1);
            return;
        }

        if (event.key === "ArrowUp") {
            if (!resultsOpen) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            setActiveIndex(activeIndex < 0 ? options.length - 1 : activeIndex - 1);
            return;
        }

        if (event.key === "PageDown" || event.key === "PageUp" || event.key === "Home" || event.key === "End") {
            if (!resultsOpen) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            if (event.key === "PageDown") {
                setActiveIndex(Math.min(options.length - 1, (activeIndex < 0 ? 0 : activeIndex) + 5));
            } else if (event.key === "PageUp") {
                setActiveIndex(Math.max(0, (activeIndex < 0 ? 0 : activeIndex) - 5));
            } else if (event.key === "Home") {
                setActiveIndex(0);
            } else {
                setActiveIndex(options.length - 1);
            }
            return;
        }

        if (event.key === "Enter") {
            if (!resultsOpen || activeIndex < 0 || !options[activeIndex]) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            const option = options[activeIndex];
            selectCliente(option.dataset.clienteId, option.dataset.clienteLabel);
            return;
        }

        if (event.key === "Escape") {
            if (resultsBox.hidden) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            closeResults();
        }
    });

    resultsBox.addEventListener("click", function (event) {
        const option = event.target.closest("[data-cliente-id]");
        if (!option) {
            return;
        }
        selectCliente(option.dataset.clienteId, option.dataset.clienteLabel);
    });
    resultsBox.addEventListener("mousemove", function (event) {
        const option = event.target.closest(".st-cliente-search-option[data-cliente-id]");
        if (!option || resultsBox.hidden) {
            return;
        }
        const options = getOptions();
        const index = options.indexOf(option);
        if (index >= 0 && index !== activeIndex) {
            setActiveIndex(index);
        }
    });

    if (clearButton) {
        clearButton.addEventListener("click", function () {
            clearCliente();
        });
    }

    if (reopenButton) {
        reopenButton.addEventListener("click", function () {
            // Riapre la ricerca senza cancellare subito: l'operatore può correggere o usare X.
            expandSearch({ focus: true });
        });
    }

    document.addEventListener("click", function (event) {
        if (!root.contains(event.target)) {
            closeResults();
        }
    });

    toggleClearButton();
    if (canCollapse && hiddenField.value) {
        collapseSearch();
    }

    const initialScript = document.getElementById("cliente-anagrafica-initial");
    if (initialScript) {
        try {
            // Apertura da lista/scheda: evidenzia scaduto in pagina, senza dialog.
            fillAnagraficaPanel(JSON.parse(initialScript.textContent), {
                skipNotify: true,
            });
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

window.labrepairSelectCliente = function (id, label) {
    const root = document.querySelector("#praticaForm [data-cliente-search-root], [data-cliente-search-root]");
    if (!root || typeof root.__labrepairSelectCliente !== "function") {
        return;
    }
    root.__labrepairSelectCliente(String(id), String(label || ""));
};
