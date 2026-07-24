(function () {
    const modal = document.getElementById("stConfirmModal");
    const titleElement = document.getElementById("stConfirmTitle");
    const messageElement = document.getElementById("stConfirmMessage");
    const iconElement = document.getElementById("stConfirmIcon");
    const iconGlyphElement = document.getElementById("stConfirmIconGlyph");
    const cancelButton = modal ? modal.querySelector("[data-st-confirm-cancel]") : null;
    const acceptButton = modal ? modal.querySelector("[data-st-confirm-accept]") : null;

    let resolver = null;

    function close(result) {
        if (!modal) {
            return;
        }

        modal.hidden = true;
        document.body.classList.remove("st-confirm-open");

        if (resolver) {
            resolver(!!result);
            resolver = null;
        }
    }

    function applyVariant(variant) {
        if (!iconElement || !iconGlyphElement) {
            return;
        }

        iconElement.classList.remove("is-info", "is-danger");
        iconGlyphElement.className = "ti";

        if (variant === "danger") {
            iconElement.classList.add("is-danger");
            iconGlyphElement.classList.add("ti-trash");
            return;
        }

        iconElement.classList.add("is-info");
        iconGlyphElement.classList.add("ti-help-circle");
    }

    function ask(options) {
        options = options || {};

        if (!modal || !titleElement || !messageElement || !acceptButton || !cancelButton) {
            return Promise.resolve(false);
        }

        titleElement.textContent = options.title || "Conferma operazione";
        messageElement.innerHTML = options.message || "";
        acceptButton.textContent = options.confirmLabel || "Conferma";
        cancelButton.textContent = options.cancelLabel || "Annulla";
        acceptButton.className = options.confirmClass || "btn btn-primary";
        applyVariant(options.variant || "info");

        modal.hidden = false;
        document.body.classList.add("st-confirm-open");
        acceptButton.focus();

        return new Promise(function (resolve) {
            resolver = resolve;
        });
    }

    if (modal && cancelButton && acceptButton) {
        cancelButton.addEventListener("click", function () {
            close(false);
        });

        acceptButton.addEventListener("click", function () {
            close(true);
        });

        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                close(false);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && modal && !modal.hidden) {
                close(false);
            }
        });
    }

    window.LabRepairConfirm = {
        ask: ask,
    };
})();
