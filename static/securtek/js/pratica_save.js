/**
 * Salva riparazione: evita il "secondo click" (blur che sposta il layout),
 * feedback Salvataggio…, anti doppio-click.
 */
(function () {
    var ACTION_SELECTOR =
        "[data-pratica-salva], [data-pratica-annulla], [data-busta-save-print], [data-embed-close], #praticaForm button[type='submit']";

    function setSavingState(form, saving) {
        if (!form) {
            return;
        }
        form.dataset.saving = saving ? "1" : "0";
        if (saving) {
            form.dataset.savingStarted = String(Date.now());
        } else {
            delete form.dataset.savingStarted;
        }
        form.querySelectorAll("[data-pratica-salva], [data-busta-save-print]").forEach(
            function (btn) {
                if (saving) {
                    if (!btn.dataset.originalHtml) {
                        btn.dataset.originalHtml = btn.innerHTML;
                    }
                    btn.disabled = true;
                    if (btn.hasAttribute("data-pratica-salva")) {
                        btn.innerHTML =
                            '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Salvataggio…';
                    }
                } else {
                    btn.disabled = false;
                    if (btn.dataset.originalHtml) {
                        btn.innerHTML = btn.dataset.originalHtml;
                        delete btn.dataset.originalHtml;
                    }
                }
            }
        );
    }

    function showBlockReason(message, options) {
        options = options || {};
        if (typeof window.labrepairShowSaveBlockReason === "function") {
            window.labrepairShowSaveBlockReason(message, options);
            return;
        }
        if (!options.forceTop) {
            return;
        }
        var form = document.getElementById("praticaForm");
        if (!form || !message) {
            return;
        }
        var existing = document.getElementById("praticaSaveClientAlert");
        if (existing) {
            existing.remove();
        }
        var alert = document.createElement("div");
        alert.id = "praticaSaveClientAlert";
        alert.className = "alert alert-danger";
        alert.setAttribute("role", "alert");
        alert.textContent = message;
        form.parentNode.insertBefore(alert, form);
    }

    function clearSaveError() {
        var existing = document.getElementById("praticaSaveClientAlert");
        if (existing) {
            existing.remove();
        }
    }

    function isAnnullaAction(action) {
        return !!(action && action.hasAttribute && action.hasAttribute("data-pratica-annulla"));
    }

    function prepareActionFlag(event) {
        if (event.button != null && event.button !== 0) {
            return;
        }
        var action = event.target && event.target.closest
            ? event.target.closest(ACTION_SELECTOR)
            : null;
        if (!action) {
            return;
        }

        // Prima del blur: blocca balloon/scroll da date e name-case.
        window.labrepairSuppressFieldBlurUi = true;
    }

    function prepareActionMouseDown(event) {
        if (event.button != null && event.button !== 0) {
            return;
        }
        var action = event.target && event.target.closest
            ? event.target.closest(ACTION_SELECTOR)
            : null;
        if (!action) {
            return;
        }

        // Solo mousedown: preventDefault su pointerdown sopprime il click.
        // Impedisce lo spostamento del focus → niente blur → niente layout shift.
        event.preventDefault();
        window.labrepairSuppressFieldBlurUi = true;

        // Su Annulla non normalizzare i campi: eviterebbe/sporcerebbe lo snapshot dirty.
        if (isAnnullaAction(action)) {
            return;
        }

        var form = document.getElementById("praticaForm");
        if (form && typeof window.labrepairCommitDateFields === "function") {
            window.labrepairCommitDateFields(form, { quiet: true });
        }
        if (window.LabRepairNameCase && typeof window.LabRepairNameCase.formatFields === "function") {
            window.LabRepairNameCase.formatFields();
        }
        if (form && typeof window.labrepairRestoreFormFieldNames === "function") {
            window.labrepairRestoreFormFieldNames(form);
        }
        if (form && typeof window.labrepairSyncNoAutofillMirrors === "function") {
            window.labrepairSyncNoAutofillMirrors(form);
        }
    }

    function releaseActionPointer() {
        window.setTimeout(function () {
            window.labrepairSuppressFieldBlurUi = false;
        }, 150);
    }

    function initPraticaSaveGuard() {
        var form = document.getElementById("praticaForm");
        if (!form || form.dataset.saveGuardBound === "1") {
            return;
        }
        form.dataset.saveGuardBound = "1";

        // Flag subito al pointerdown (prima di blur), senza preventDefault.
        document.addEventListener("pointerdown", prepareActionFlag, true);
        // Blocco focus/blur solo su mousedown (il click resta valido).
        document.addEventListener("mousedown", prepareActionMouseDown, true);
        document.addEventListener("mouseup", releaseActionPointer, true);
        document.addEventListener("pointerup", releaseActionPointer, true);
        document.addEventListener("pointercancel", releaseActionPointer, true);

        form.addEventListener(
            "submit",
            function (event) {
                if (form.dataset.saving === "1") {
                    event.preventDefault();
                    event.stopPropagation();
                    showBlockReason(
                        "Salvataggio già in corso, attendere.",
                        { forceTop: true }
                    );
                    return;
                }
                if (
                    typeof window.labrepairNeedsDocumentoScadutoForce === "function" &&
                    window.labrepairNeedsDocumentoScadutoForce()
                ) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    setSavingState(form, false);
                    if (typeof window.labrepairPromptDocumentoScadutoForce === "function") {
                        window.labrepairPromptDocumentoScadutoForce().then(function (forza) {
                            if (forza) {
                                form.requestSubmit
                                    ? form.requestSubmit()
                                    : form.submit();
                            }
                        });
                    }
                    return;
                }
                clearSaveError();
                if (typeof window.labrepairRestoreFormFieldNames === "function") {
                    window.labrepairRestoreFormFieldNames(form);
                }
                if (typeof window.labrepairSyncNoAutofillMirrors === "function") {
                    window.labrepairSyncNoAutofillMirrors(form);
                }
            },
            true
        );

        form.addEventListener("submit", function (event) {
            if (event.defaultPrevented) {
                setSavingState(form, false);
                // Messaggi già mostrati accanto ai campi dalla validazione.
                return;
            }

            if (typeof window.markLabRepairLeavingPage === "function") {
                window.markLabRepairLeavingPage();
            }
            setSavingState(form, true);
        });

        window.setInterval(function () {
            if (form.dataset.saving !== "1") {
                return;
            }
            var started = parseInt(form.dataset.savingStarted || "0", 10);
            if (!started) {
                return;
            }
            if (Date.now() - started > 15000) {
                setSavingState(form, false);
                showBlockReason(
                    "Timeout di rete o server. Riprova.",
                    { forceTop: true }
                );
            }
        }, 2000);
    }

    document.addEventListener("DOMContentLoaded", initPraticaSaveGuard);
})();
