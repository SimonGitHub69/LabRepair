(function () {
    const form = document.getElementById("praticaForm");
    if (!form) {
        return;
    }

    let dirty = false;
    let initialSnapshot = "";
    let allowingLeave = false;
    let suppressDirty = true;
    let annullaWasDirty = false;

    function withRestoredNames(callback) {
        const restore =
            typeof window.labrepairRestoreFormFieldNames === "function"
                ? window.labrepairRestoreFormFieldNames
                : null;
        const scramble =
            typeof window.labrepairRescrambleFormFieldNames === "function"
                ? window.labrepairRescrambleFormFieldNames
                : null;
        if (restore) {
            restore(form);
        }
        try {
            return callback();
        } finally {
            if (scramble) {
                scramble(form);
            }
        }
    }

    function snapshotForm() {
        return withRestoredNames(function () {
            if (typeof window.labrepairSyncNoAutofillMirrors === "function") {
                window.labrepairSyncNoAutofillMirrors(form);
            }
            const data = new FormData(form);
            const parts = [];
            data.forEach(function (value, key) {
                if (typeof File !== "undefined" && value instanceof File) {
                    parts.push(
                        key +
                            "=file:" +
                            (value.name || "") +
                            ":" +
                            String(value.size || 0)
                    );
                    return;
                }
                parts.push(key + "=" + String(value == null ? "" : value));
            });
            parts.sort();
            return parts.join("\n");
        });
    }

    function refreshInitialSnapshot() {
        initialSnapshot = snapshotForm();
        dirty = false;
    }

    function isDirty() {
        if (allowingLeave) {
            return false;
        }
        if (dirty) {
            return true;
        }
        try {
            return snapshotForm() !== initialSnapshot;
        } catch (error) {
            return dirty;
        }
    }

    function markDirty() {
        if (suppressDirty || allowingLeave) {
            return;
        }
        dirty = true;
    }

    function askLeaveWithoutSaving() {
        const message =
            "Hai effettuato modifiche non salvate sulla scheda.<br>" +
            "Premi <strong>Torna indietro</strong> per restare e salvare, " +
            "oppure <strong>Esci senza salvare</strong> per perdere le modifiche.";

        if (window.LabRepairConfirm && typeof window.LabRepairConfirm.ask === "function") {
            return window.LabRepairConfirm.ask({
                title: "Modifiche non salvate",
                message: message,
                confirmLabel: "Esci senza salvare",
                cancelLabel: "Torna indietro",
                confirmClass: "btn btn-danger",
                variant: "danger",
            });
        }

        return Promise.resolve(
            window.confirm(
                "Hai effettuato modifiche non salvate.\n\nOK = esci senza salvare\nAnnulla = torna indietro per salvare"
            )
        );
    }

    function leaveTo(url) {
        allowingLeave = true;
        dirty = false;
        if (typeof window.markLabRepairLeavingPage === "function") {
            window.markLabRepairLeavingPage();
        }
        window.location.href = url;
    }

    function annullaHref(link) {
        return link.getAttribute("href") || "";
    }

    function shouldPromptLeave(link) {
        // pointerdown cattura lo stato PRIMA del blur (name-case / date)
        // che altrimenti marca dirty e fa apparire il dialogo al primo Annulla.
        if (link && link.dataset.annullaDirtyCaptured === "1") {
            return link.dataset.annullaWasDirty === "1";
        }
        return isDirty();
    }

    form.addEventListener("input", markDirty, true);
    form.addEventListener("change", markDirty, true);

    form.addEventListener("submit", function () {
        allowingLeave = true;
        dirty = false;
    });

    document.querySelectorAll("[data-pratica-annulla]").forEach(function (link) {
        link.addEventListener(
            "pointerdown",
            function (event) {
                if (event.button != null && event.button !== 0) {
                    return;
                }
                const href = annullaHref(link);
                if (!href || href === "#") {
                    return;
                }
                annullaWasDirty = isDirty();
                link.dataset.annullaDirtyCaptured = "1";
                link.dataset.annullaWasDirty = annullaWasDirty ? "1" : "0";
            },
            true
        );

        link.addEventListener("click", function (event) {
            const href = annullaHref(link);
            if (!href || href === "#") {
                return;
            }

            const needsPrompt = shouldPromptLeave(link);
            link.dataset.annullaDirtyCaptured = "0";

            if (!needsPrompt) {
                allowingLeave = true;
                dirty = false;
                return;
            }

            event.preventDefault();
            event.stopImmediatePropagation();

            askLeaveWithoutSaving().then(function (leave) {
                if (leave) {
                    leaveTo(href);
                }
            });
        });
    });

    window.labrepairPraticaFormIsDirty = isDirty;
    window.labrepairPraticaFormMarkClean = refreshInitialSnapshot;

    function finishBootstrap() {
        refreshInitialSnapshot();
        suppressDirty = false;
    }

    function scheduleBootstrap() {
        // Dopo enhance date / sync consegna / sezioni collassabili il form
        // può cambiare senza intervento utente: rilancia lo snapshot.
        window.setTimeout(finishBootstrap, 50);
        window.setTimeout(finishBootstrap, 300);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", scheduleBootstrap);
    } else {
        scheduleBootstrap();
    }
})();
