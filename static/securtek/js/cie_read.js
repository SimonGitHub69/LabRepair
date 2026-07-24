(function () {
    const modal = document.getElementById("cieReadModal");
    const openButtons = document.querySelectorAll("[data-cie-read-open]");
    if (!modal || !openButtons.length) {
        return;
    }

    const canInput = document.getElementById("cieCanInput");
    const statusEl = document.getElementById("cieReadStatus");
    const submitBtn = modal.querySelector("[data-cie-read-submit]");
    const cancelButtons = modal.querySelectorAll("[data-cie-read-cancel]");
    const serverEndpoint = modal.dataset.cieUrl || "";
    const localBase =
        (modal.dataset.cieLocalUrl || "http://127.0.0.1:17345").replace(/\/$/, "");
    const preferServer = modal.dataset.ciePreferServer === "1";
    const localReadUrl = localBase + "/read";
    const localHealthUrl = localBase + "/health";

    function getCsrfToken() {
        const cookie = document.cookie
            .split(";")
            .map(function (part) {
                return part.trim();
            })
            .find(function (part) {
                return part.startsWith("csrftoken=");
            });
        if (cookie) {
            return decodeURIComponent(cookie.slice("csrftoken=".length));
        }
        const hidden = document.querySelector("#anagraficaForm input[name=csrfmiddlewaretoken]");
        return hidden ? hidden.value : "";
    }

    function setStatus(message, isError) {
        if (!statusEl) {
            return;
        }
        statusEl.textContent = message || "";
        statusEl.classList.toggle("text-danger", !!isError);
        statusEl.classList.toggle("text-secondary", !isError);
    }

    async function openModal() {
        modal.hidden = false;
        document.body.classList.add("st-confirm-open");
        setStatus("Verifica agent CIE…", false);
        if (submitBtn) {
            submitBtn.disabled = false;
        }
        if (canInput) {
            canInput.value = "";
            canInput.focus();
        }
        const localOk = preferServer ? false : await isLocalAgentAvailable();
        if (preferServer) {
            setStatus(
                "Poggia la CIE sul lettore collegato al server, poi inserisci il CAN (6 cifre).",
                false
            );
        } else if (localOk) {
            setStatus(
                "Poggia la CIE sul lettore Bit4id, poi inserisci il CAN (6 cifre).",
                false
            );
        } else {
            setStatus(
                "Agent CIE non attivo su questo PC. " +
                    "Sul PC con il Bit4id esegui install_cie_agent_client.ps1 " +
                    "(o avvia LabRepair CIE Agent dal Desktop), poi riprova.",
                true
            );
        }
    }

    function closeModal() {
        modal.hidden = true;
        document.body.classList.remove("st-confirm-open");
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }

    function setFieldValue(name, value) {
        if (value === null || value === undefined || value === "") {
            return;
        }
        const field = document.getElementById("id_" + name);
        if (!field) {
            return;
        }
        field.value = value;
        field.dispatchEvent(new Event("change", { bubbles: true }));
        field.dispatchEvent(new Event("input", { bubbles: true }));
        if (typeof window.labrepairSyncNoAutofillMirrors === "function") {
            window.labrepairSyncNoAutofillMirrors(field.form || document.getElementById("anagraficaForm"));
        }
    }

    function setIndirizzo(data) {
        if (!data) {
            return;
        }

        if (!data.cap && data.indirizzo_raw) {
            const match = String(data.indirizzo_raw).match(/\b(\d{5})\b/);
            if (match) {
                data.cap = match[1];
            }
        }

        const mapping = {
            indirizzo: "indirizzo",
            civico: "civico",
            cap: "cap",
            comune: "comune",
            provincia: "provincia",
            tipo: "tipo",
        };
        Object.keys(mapping).forEach(function (key) {
            const value = data[key];
            if (!value) {
                return;
            }
            const field =
                document.getElementById("id_indirizzi-0-" + mapping[key]) ||
                document.querySelector('[id^="id_indirizzi-"][id$="-' + mapping[key] + '"]');
            if (field) {
                field.value = value;
                field.dispatchEvent(new Event("change", { bubbles: true }));
                field.dispatchEvent(new Event("input", { bubbles: true }));
            }
        });
    }

    function applyCieData(data) {
        [
            "cognome",
            "nome",
            "sesso",
            "data_nascita",
            "luogo_nascita",
            "provincia_nascita",
            "codice_fiscale",
            "documento_tipo",
            "documento_numero",
            "documento_data_rilascio",
            "documento_data_scadenza",
            "documento_rilasciato_da",
        ].forEach(function (name) {
            setFieldValue(name, data[name]);
        });

        if (window.LabRepairNameCase && typeof window.LabRepairNameCase.formatFields === "function") {
            window.LabRepairNameCase.formatFields();
        }

        const indirizzo = data.indirizzo || null;
        if (indirizzo && data.indirizzo_raw) {
            indirizzo.indirizzo_raw = data.indirizzo_raw;
        }
        setIndirizzo(indirizzo);
    }

    function fetchWithTimeout(url, options, timeoutMs) {
        const controller = new AbortController();
        const timer = setTimeout(function () {
            controller.abort();
        }, timeoutMs);
        const opts = Object.assign({}, options || {}, { signal: controller.signal });
        return fetch(url, opts).finally(function () {
            clearTimeout(timer);
        });
    }

    async function isLocalAgentAvailable() {
        try {
            const response = await fetchWithTimeout(
                localHealthUrl,
                { method: "GET", mode: "cors", cache: "no-store" },
                800
            );
            if (!response.ok) {
                return false;
            }
            const payload = await response.json().catch(function () {
                return {};
            });
            return !!payload.ok;
        } catch (error) {
            return false;
        }
    }

    async function readFromLocal(can) {
        const response = await fetchWithTimeout(
            localReadUrl,
            {
                method: "POST",
                mode: "cors",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ can: can }),
            },
            50000
        );
        const payload = await response.json().catch(function () {
            return {};
        });
        if (!response.ok || !payload.ok) {
            throw new Error(payload.message || "Lettura CIE non riuscita (agent locale).");
        }
        return payload.data || {};
    }

    async function readFromServer(can) {
        if (!serverEndpoint) {
            throw new Error(
                "Agent CIE non avviato su questo PC. Esegui cie_reader.exe --serve " +
                    "nella cartella tools/cie_reader/publish."
            );
        }

        const response = await fetch(serverEndpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({ can: can }),
            credentials: "same-origin",
        });
        const payload = await response.json().catch(function () {
            return {};
        });
        if (!response.ok || !payload.ok) {
            throw new Error(payload.message || "Lettura CIE non riuscita.");
        }
        return payload.data || {};
    }

    async function readCie() {
        const can = (canInput && canInput.value ? canInput.value : "").trim();
        if (!/^\d{6}$/.test(can)) {
            setStatus("Inserisci il CAN di 6 cifre stampato sul fronte della CIE.", true);
            if (canInput) {
                canInput.focus();
            }
            return;
        }

        if (submitBtn) {
            submitBtn.disabled = true;
        }
        setStatus("Lettura in corso… tieni la CIE sul lettore.", false);

        try {
            // Lettore sul server: sempre Django. Altrimenti agent locale sul PC.
            let data;
            if (!preferServer && (await isLocalAgentAvailable())) {
                data = await readFromLocal(can);
            } else {
                data = await readFromServer(can);
            }
            applyCieData(data || {});
            closeModal();
        } catch (error) {
            let message = error.message || "Lettura CIE non riuscita.";
            if (
                error.name === "AbortError" ||
                /Failed to fetch|NetworkError|Load failed/i.test(String(error.message || ""))
            ) {
                message =
                    "Agent CIE non raggiungibile su questo PC. " +
                    "Installa/avvia l'agent sul computer con il lettore Bit4id " +
                    "(script install_cie_agent_client.ps1 o collegamento LabRepair CIE Agent).";
            }
            setStatus(message, true);
            if (submitBtn) {
                submitBtn.disabled = false;
            }
        }
    }

    openButtons.forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            openModal();
        });
    });

    cancelButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            closeModal();
        });
    });

    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modal.hidden) {
            closeModal();
        }
    });

    if (submitBtn) {
        submitBtn.addEventListener("click", function () {
            readCie();
        });
    }

    if (canInput) {
        canInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                readCie();
            }
        });
    }
})();
