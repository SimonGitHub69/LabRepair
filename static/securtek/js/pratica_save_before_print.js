(function () {
    function cancelledError(message) {
        var err = new Error(message || "Operazione annullata.");
        err.labrepairCancelled = true;
        return err;
    }

    /**
     * Salva #praticaForm via AJAX se presente (pagina modifica).
     * Usa la stessa validazione del pulsante Salva.
     * Sulla scheda dettaglio non c'è form: resolve immediato.
     *
     * options.skipClientValidation: se true, non ripete la validazione
     * (utile quando il chiamante l'ha già eseguita a monte).
     */
    window.labrepairSavePraticaForm = function (options) {
        options = options || {};
        return new Promise(function (resolve, reject) {
            var form = document.getElementById("praticaForm");
            if (!form) {
                resolve({ ok: true, skipped: true });
                return;
            }

            if (!options.skipClientValidation) {
                if (
                    typeof window.labrepairNeedsSenzaTelefonoForce === "function" &&
                    window.labrepairNeedsSenzaTelefonoForce()
                ) {
                    var promptTelefono =
                        typeof window.labrepairPromptSenzaTelefonoForce === "function"
                            ? window.labrepairPromptSenzaTelefonoForce()
                            : Promise.resolve(false);
                    promptTelefono.then(function (forza) {
                        if (!forza) {
                            reject(cancelledError());
                            return;
                        }
                        window
                            .labrepairSavePraticaForm(
                                Object.assign({}, options, {
                                    skipClientValidation: false,
                                    _telefonoForced: true,
                                })
                            )
                            .then(resolve, reject);
                    });
                    return;
                }
                if (typeof window.labrepairValidatePraticaForm === "function") {
                    var validation = window.labrepairValidatePraticaForm();
                    if (!validation.ok) {
                        if (
                            validation.reason === "telefono" &&
                            typeof window.labrepairPromptSenzaTelefonoForce ===
                                "function"
                        ) {
                            window
                                .labrepairPromptSenzaTelefonoForce()
                                .then(function (forza) {
                                    if (!forza) {
                                        reject(cancelledError());
                                        return;
                                    }
                                    window
                                        .labrepairSavePraticaForm(
                                            Object.assign({}, options, {
                                                skipClientValidation: false,
                                            })
                                        )
                                        .then(resolve, reject);
                                });
                            return;
                        }
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

                    if (
                        payload.cliente_id &&
                        typeof window.labrepairSelectCliente === "function"
                    ) {
                        window.labrepairSelectCliente(
                            payload.cliente_id,
                            payload.cliente_label || ""
                        );
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
