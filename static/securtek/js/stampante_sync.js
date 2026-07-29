(function () {
    const form = document.getElementById("stampanteSyncForm");
    if (!form) {
        return;
    }

    const agentUrl = (form.dataset.agentUrl || "http://127.0.0.1:17346").replace(/\/$/, "");
    const csrfInput = form.querySelector("input[name=csrfmiddlewaretoken]");
    const submitButton = form.querySelector("[type=submit]");

    async function syncFromLocalAgent() {
        const response = await fetch(agentUrl + "/printers", {
            method: "GET",
            credentials: "omit",
        });
        if (!response.ok) {
            throw new Error("Agent stampanti non disponibile");
        }

        const payload = await response.json();
        const printers = payload && payload.printers ? payload.printers : [];
        if (!printers.length) {
            throw new Error("Nessuna stampante rilevata sul PC");
        }

        const body = new FormData();
        if (csrfInput) {
            body.append("csrfmiddlewaretoken", csrfInput.value);
        }
        body.append("printers_json", JSON.stringify({ printers: printers }));

        const syncResponse = await fetch(form.action, {
            method: "POST",
            body: body,
            credentials: "same-origin",
        });

        if (syncResponse.redirected) {
            window.location.href = syncResponse.url;
            return;
        }
        if (!syncResponse.ok) {
            throw new Error("Impossibile salvare le stampanti rilevate");
        }
        window.location.reload();
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (submitButton) {
            submitButton.disabled = true;
        }

        syncFromLocalAgent()
            .catch(function () {
                form.submit();
            })
            .finally(function () {
                if (submitButton) {
                    submitButton.disabled = false;
                }
            });
    });
})();
