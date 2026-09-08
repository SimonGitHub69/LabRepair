(function () {
    const form = document.getElementById("praticaForm");
    if (!form) {
        return;
    }

    let dirty = false;
    let initialSnapshot = "";
    let allowingLeave = false;

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

    form.addEventListener("input", markDirty, true);
    form.addEventListener("change", markDirty, true);

    form.addEventListener("submit", function () {
        allowingLeave = true;
        dirty = false;
    });

    document.querySelectorAll("[data-pratica-annulla]").forEach(function (link) {
        link.addEventListener("click", function (event) {
            const href = link.getAttribute("href") || "";
            if (!href || href === "#") {
                return;
            }
            if (!isDirty()) {
                allowingLeave = true;
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

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            window.setTimeout(refreshInitialSnapshot, 50);
        });
    } else {
        window.setTimeout(refreshInitialSnapshot, 50);
    }
})();
