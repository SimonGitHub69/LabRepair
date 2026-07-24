(function () {
    /**
     * Salva #praticaForm via AJAX se presente (pagina modifica).
     * Usa la stessa validazione del pulsante Salva.
     * Sulla scheda dettaglio non c'è form: resolve immediato.
     */
    window.labrepairSavePraticaForm = function () {
        return new Promise(function (resolve, reject) {
            var form = document.getElementById("praticaForm");
            if (!form) {
                resolve({ ok: true, skipped: true });
                return;
            }

            if (typeof window.labrepairValidatePraticaForm === "function") {
                var validation = window.labrepairValidatePraticaForm();
                if (!validation.ok) {
                    reject(
                        new Error(
                            validation.message ||
                                "Compila i campi obbligatori prima di stampare."
                        )
                    );
                    return;
                }
            } else if (
                typeof form.reportValidity === "function" &&
                !form.reportValidity()
            ) {
                reject(new Error("Compila i campi obbligatori prima di stampare."));
                return;
            }

            var action = form.getAttribute("action") || window.location.href;
            if (typeof window.labrepairRestoreFormFieldNames === "function") {
                window.labrepairRestoreFormFieldNames(form);
            }
            if (typeof window.labrepairSyncNoAutofillMirrors === "function") {
                window.labrepairSyncNoAutofillMirrors(form);
            }
            var formData = new FormData(form);
            if (typeof window.labrepairRescrambleFormFieldNames === "function") {
                window.labrepairRescrambleFormFieldNames(form);
            }

            fetch(action, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "X-Requested-With": "XMLHttpRequest",
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
                    var response = result.response;
                    var payload = result.payload;

                    if (payload.redirect_url) {
                        window.location.href = payload.redirect_url;
                        reject(new Error(payload.message || "Reindirizzamento…"));
                        return;
                    }

                    if (!response.ok || !payload.ok) {
                        reject(
                            new Error(
                                payload.message ||
                                    "Impossibile salvare la scheda prima della stampa."
                            )
                        );
                        return;
                    }

                    resolve(payload);
                })
                .catch(function (error) {
                    if (error && error.message) {
                        reject(error);
                        return;
                    }
                    reject(new Error("Errore di rete durante il salvataggio."));
                });
        });
    };
})();
