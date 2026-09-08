(function () {
    function minHeightForRows(field, rows) {
        const styles = window.getComputedStyle(field);
        const lineHeight = parseFloat(styles.lineHeight) || 20;
        const paddingTop = parseFloat(styles.paddingTop) || 0;
        const paddingBottom = parseFloat(styles.paddingBottom) || 0;
        const borderTop = parseFloat(styles.borderTopWidth) || 0;
        const borderBottom = parseFloat(styles.borderBottomWidth) || 0;
        return Math.ceil(lineHeight * rows + paddingTop + paddingBottom + borderTop + borderBottom);
    }

    function autosizeField(field) {
        if (!field || field.tagName !== "TEXTAREA") {
            return;
        }
        const root = field.closest("[data-textarea-expand]");
        if (root && root.classList.contains("is-expanded")) {
            field.style.height = "";
            return;
        }

        const minRows = Number(field.getAttribute("rows") || field.dataset.autosizeMinRows || 2);
        const minHeight = minHeightForRows(field, minRows);
        field.style.height = "auto";
        field.style.height = Math.max(field.scrollHeight, minHeight) + "px";
    }

    function bindAutosize(field) {
        if (!field || field.dataset.autosizeBound === "1") {
            return;
        }
        field.dataset.autosizeBound = "1";
        field.classList.add("st-autosize");
        field.addEventListener("input", function () {
            autosizeField(field);
        });
        field.addEventListener("change", function () {
            autosizeField(field);
        });
        autosizeField(field);
    }

    function setExpanded(root, expanded) {
        const col = root.closest("[data-textarea-expand-col]");
        const btn = root.querySelector("[data-textarea-expand-btn]");
        const icon = root.querySelector("[data-textarea-expand-icon]");
        const label = root.querySelector("[data-textarea-expand-label]");
        const field = root.querySelector("textarea");
        const fieldLabel = root.querySelector(".form-label");
        const name = fieldLabel ? fieldLabel.textContent.replace(/\s*\*\s*$/, "").trim() : "campo";

        root.classList.toggle("is-expanded", expanded);
        if (col) {
            col.classList.toggle("st-textarea-col-expanded", expanded);
        }
        if (btn) {
            btn.setAttribute("aria-expanded", expanded ? "true" : "false");
            btn.setAttribute("title", expanded ? "Riduci " + name : "Allarga " + name);
            btn.setAttribute("aria-label", expanded ? "Riduci " + name : "Allarga " + name);
        }
        if (icon) {
            icon.classList.toggle("ti-arrows-maximize", !expanded);
            icon.classList.toggle("ti-arrows-minimize", expanded);
        }
        if (label) {
            label.textContent = expanded ? "Riduci" : "Allarga";
        }
        if (field) {
            if (expanded) {
                field.style.height = "";
                if (!field.dataset.rowsCollapsed) {
                    field.dataset.rowsCollapsed = String(field.rows || 3);
                }
                field.rows = Math.max(Number(field.dataset.rowsCollapsed) || 3, 10);
            } else if (field.dataset.rowsCollapsed) {
                field.rows = Number(field.dataset.rowsCollapsed) || 3;
                autosizeField(field);
            }
        }
    }

    document.querySelectorAll("[data-textarea-expand]").forEach(function (root) {
        const btn = root.querySelector("[data-textarea-expand-btn]");
        const field = root.querySelector("textarea");
        if (field) {
            bindAutosize(field);
        }
        if (!btn) {
            return;
        }
        btn.addEventListener("click", function () {
            setExpanded(root, !root.classList.contains("is-expanded"));
        });
    });

    document.querySelectorAll("textarea.st-autosize, textarea[data-autosize]").forEach(bindAutosize);

    window.LabRepairAutosizeTextarea = {
        bind: bindAutosize,
        resize: autosizeField,
    };
})();
