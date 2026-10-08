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
    const searchScope = (root.dataset.searchScope || "").trim();
    const searchNegozioFieldId = (root.dataset.searchNegozioField || "").trim();
    const referenteUrlTemplate = root.dataset.referenteUrlTemplate || "";

    if (!hiddenField || !searchInput || !resultsBox || !searchUrl) {
        return;
    }

    function buildSearchParams(extra) {
        const params = Object.assign({}, extra || {});
        if (searchScope) {
            params.scope = searchScope;
        }
        if (searchNegozioFieldId) {
            const negozioField = document.getElementById(searchNegozioFieldId);
            const negozioValue = negozioField ? String(negozioField.value || "").trim() : "";
            if (negozioValue && negozioValue.toLowerCase() !== "all") {
                params.negozio = negozioValue;
            }
        }
        return params;
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
        if (isClienteLocked()) {
            // Con testata bloccata non mostrare «Cambia cliente».
            summaryBox.hidden = true;
            if (reopenButton) {
                reopenButton.hidden = true;
            }
            if (clearButton) {
                clearButton.hidden = true;
            }
        } else {
            summaryBox.hidden = false;
        }
        closeResults();
        root.classList.add("is-cliente-selected");
    }

    function isClienteLocked() {
        return root.dataset.clienteLocked === "1";
    }

    function notifyClienteChanged(id) {
        if (getFilterForm()) {
            return;
        }
        document.dispatchEvent(new CustomEvent("labrepair:cliente-changed", {
            detail: { id: id || "" },
        }));
    }

    function expandSearch(options) {
        if (isClienteLocked() || !canCollapse || !searchPanel || !summaryBox) {
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
        clearResultsPosition();
    }

    function renderMessage(message) {
        activeIndex = -1;
        resultsBox.innerHTML = `<div class="st-cliente-search-empty">${message}</div>`;
        resultsBox.hidden = false;
        setResultsOpen(true);
        positionFilterResults();
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
        positionFilterResults();
        setActiveIndex(0);
    }

    function getFilterForm() {
        // Il form è dentro .st-pratica-filter-card; non esiste un elemento
        // che sia contemporaneamente card e form (closest(".card form") fallisce).
        if (!root.closest(".st-pratica-filter-card")) {
            return null;
        }
        return root.closest("form");
    }

    function submitFilterForm() {
        const filterForm = getFilterForm();
        if (filterForm) {
            filterForm.requestSubmit();
        }
    }

    function clearResultsPosition() {
        resultsBox.style.position = "";
        resultsBox.style.left = "";
        resultsBox.style.top = "";
        resultsBox.style.width = "";
        resultsBox.style.right = "";
        resultsBox.style.zIndex = "";
    }

    function positionFilterResults() {
        if (!getFilterForm()) {
            clearResultsPosition();
            return;
        }
        const anchor = searchInput.getBoundingClientRect();
        const width = Math.max(anchor.width, 280);
        let left = anchor.left;
        if (left + width > window.innerWidth - 8) {
            left = Math.max(8, window.innerWidth - width - 8);
        }
        resultsBox.style.position = "fixed";
        resultsBox.style.left = left + "px";
        resultsBox.style.top = anchor.bottom + 4 + "px";
        resultsBox.style.width = width + "px";
        resultsBox.style.right = "auto";
        resultsBox.style.zIndex = "2400";
    }

    function syncFilterSubmitFromText() {
        const filterForm = getFilterForm();
        if (!filterForm || hiddenField.value) {
            return;
        }
        const text = searchInput.value.trim();
        if (!text) {
            return;
        }
        const qField = filterForm.querySelector('input[name="q"]');
        if (qField && !String(qField.value || "").trim()) {
            qField.value = text;
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
        if (isClienteLocked()) {
            return;
        }
        hiddenField.value = id;
        searchInput.value = label;
        searchInput.dataset.selectedLabel = label;
        closeResults();
        toggleClearButton();
        notifyClienteChanged(id);
        fetchReferente(id).finally(function () {
            collapseSearch();
            focusReferenteCognome();
        });
        submitFilterForm();
    }

    root.__labrepairSelectCliente = selectCliente;

    function clearCliente(options) {
        if (isClienteLocked()) {
            return;
        }
        options = options || {};
        hiddenField.value = "";
        searchInput.value = "";
        delete searchInput.dataset.selectedLabel;
        closeResults();
        toggleClearButton();
        notifyClienteChanged("");
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
        if (isClienteLocked()) {
            return;
        }
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
            fetchResults(buildSearchParams({q: query}));
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
        if (!root.contains(event.target) && !resultsBox.contains(event.target)) {
            closeResults();
        }
    });

    window.addEventListener(
        "scroll",
        function () {
            if (!resultsBox.hidden) {
                positionFilterResults();
            }
        },
        true
    );
    window.addEventListener("resize", function () {
        if (!resultsBox.hidden) {
            positionFilterResults();
        }
    });

    const filterFormForSubmit = getFilterForm();
    if (filterFormForSubmit) {
        filterFormForSubmit.addEventListener("submit", function () {
            syncFilterSubmitFromText();
        });
    }

    toggleClearButton();
    if (canCollapse && hiddenField.value) {
        collapseSearch();
    }
    if (isClienteLocked()) {
        root.classList.add("is-cliente-locked");
        const col = root.closest("[data-cliente-search-col]");
        if (col) {
            col.hidden = true;
        }
        if (searchPanel) {
            searchPanel.hidden = true;
        }
        if (summaryBox) {
            summaryBox.hidden = true;
        }
        if (reopenButton) {
            reopenButton.hidden = true;
        }
        if (clearButton) {
            clearButton.hidden = true;
        }
        searchInput.readOnly = true;
        root.querySelectorAll("[data-cliente-locked-name], .mb-2").forEach(function (el) {
            if (el.querySelector && el.querySelector('input[readonly], input[aria-disabled="true"]')) {
                const label = el.querySelector("label");
                if (label && (label.textContent || "").trim() === "Cliente") {
                    el.remove();
                }
            }
        });
    }

    // Rimuove banner «Testata bloccata» residui da cache/vecchie versioni.
    document.querySelectorAll("[data-pratica-testata] [data-testata-locked-hint]").forEach(function (el) {
        if (el.tagName === "I" && el.closest(".st-form-section-icon")) {
            return;
        }
        el.remove();
    });
    document.querySelectorAll("[data-pratica-testata] .alert").forEach(function (el) {
        if ((el.textContent || "").indexOf("Testata bloccata") >= 0) {
            el.remove();
        }
    });

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
    if (!root || root.dataset.clienteLocked === "1" || typeof root.__labrepairSelectCliente !== "function") {
        return;
    }
    root.__labrepairSelectCliente(String(id), String(label || ""));
};

window.labrepairLockTestata = function (payload) {
    payload = payload || {};
    const fieldIds = [
        "id_operatore",
        "id_referente_cognome",
        "id_referente_nome",
        "id_referente_telefono",
        "id_referente_cellulare",
        "id_referente_email",
        "id_data_apertura",
    ];
    const valueById = {
        id_referente_cognome: payload.referente_cognome,
        id_referente_nome: payload.referente_nome,
        id_referente_telefono: payload.referente_telefono,
        id_referente_cellulare: payload.referente_cellulare,
        id_referente_email: payload.referente_email,
        id_operatore: payload.operatore_id,
        id_data_apertura: payload.data_apertura,
    };

    fieldIds.forEach(function (id) {
        const field = document.getElementById(id);
        if (!field) {
            return;
        }
        if (valueById[id] != null && valueById[id] !== "") {
            field.value = valueById[id];
        }
        if (id === "id_operatore" && !String(field.value || "").trim()) {
            return;
        }
        field.readOnly = true;
        field.disabled = true;
        field.setAttribute("aria-disabled", "true");

        const dateWrap = field.closest(".st-date-field");
        if (dateWrap) {
            dateWrap.classList.add("is-locked");
            const textField = dateWrap.querySelector(".st-date-text");
            if (textField) {
                textField.readOnly = true;
                textField.disabled = true;
                textField.setAttribute("aria-disabled", "true");
            }
            const calBtn = dateWrap.querySelector(".st-date-calendar-btn");
            if (calBtn) {
                calBtn.hidden = true;
            }
        }
    });

    const testata = document.querySelector("[data-pratica-testata]");
    if (testata) {
        testata.dataset.testataLocked = "1";
        testata.classList.add("is-testata-locked");
        // Rimuove eventuali banner testo residui da versioni precedenti.
        testata.querySelectorAll("[data-testata-locked-hint]").forEach(function (el) {
            if (el.tagName !== "I" || !el.closest(".st-form-section-icon")) {
                el.remove();
            }
        });
        const iconWrap = testata.querySelector(".st-form-section-icon");
        if (iconWrap) {
            iconWrap.classList.add("is-locked");
            let hint = iconWrap.querySelector("[data-testata-locked-hint]");
            if (!hint) {
                iconWrap.innerHTML = "";
                hint = document.createElement("i");
                hint.className = "ti ti-lock";
                hint.setAttribute("data-testata-locked-hint", "1");
                hint.setAttribute("title", "Testata bloccata: busta stampata oppure riparazione evasa");
                hint.setAttribute("aria-label", "Testata bloccata");
                iconWrap.appendChild(hint);
            }
        }
    }

    document.querySelectorAll("[data-cliente-search-root]").forEach(function (root) {
        root.dataset.clienteLocked = "1";
        root.classList.add("is-cliente-locked");
        root.querySelectorAll("[data-cliente-locked-name]").forEach(function (el) {
            el.remove();
        });
        const col = root.closest("[data-cliente-search-col]");
        if (col) {
            col.hidden = true;
        }
        const hidden = root.querySelector('input[type="hidden"][name="cliente"]');
        if (hidden && payload.cliente_id != null) {
            hidden.value = payload.cliente_id ? String(payload.cliente_id) : "";
        }
        const reopen = root.querySelector("[data-cliente-search-reopen]");
        if (reopen) {
            reopen.hidden = true;
        }
        const summary = root.querySelector("[data-cliente-search-summary]");
        if (summary) {
            summary.hidden = true;
        }
        const clearButton = root.querySelector("[data-cliente-search-clear]");
        if (clearButton) {
            clearButton.hidden = true;
        }
        const nuovo = root.querySelector(".js-nuovo-cliente-link");
        if (nuovo) {
            nuovo.hidden = true;
        }
        const panel = root.querySelector("[data-cliente-search-panel]");
        if (panel) {
            panel.hidden = true;
        }
        const searchInput = root.querySelector("[data-cliente-search-input]");
        if (searchInput) {
            searchInput.readOnly = true;
        }
    });
};

window.labrepairLockCliente = window.labrepairLockTestata;

document.addEventListener("DOMContentLoaded", function () {
    const testata = document.querySelector("[data-pratica-testata]");
    if (!testata || testata.dataset.testataLocked === "1") {
        return;
    }
    const evasaChecked = document.querySelector(
        'input[type="radio"][name="stato"][value="evasa"]:checked'
    );
    const statoSelect = document.getElementById("id_stato");
    const evasaSelected =
        !!evasaChecked ||
        (statoSelect && statoSelect.tagName === "SELECT" && statoSelect.value === "evasa");
    if (evasaSelected && typeof window.labrepairLockTestata === "function") {
        window.labrepairLockTestata({});
    }
});
