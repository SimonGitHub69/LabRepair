(function (window) {
    "use strict";

    function formatCognome(value) {
        return String(value || "")
            .trim()
            .toLocaleUpperCase("it-IT");
    }

    function formatNome(value) {
        return String(value || "")
            .trim()
            .split(/\s+/)
            .filter(Boolean)
            .map(function (word) {
                if (!word) {
                    return "";
                }
                return (
                    word.charAt(0).toLocaleUpperCase("it-IT") +
                    word.slice(1).toLocaleLowerCase("it-IT")
                );
            })
            .join(" ");
    }

    function applyToInput(input, formatter) {
        if (!input || input.disabled || input.readOnly) {
            return;
        }
        const next = formatter(input.value);
        if (next === input.value) {
            return;
        }
        input.value = next;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function bind(cognomeInput, nomeInput) {
        const cognome =
            typeof cognomeInput === "string"
                ? document.querySelector(cognomeInput)
                : cognomeInput;
        const nome =
            typeof nomeInput === "string" ? document.querySelector(nomeInput) : nomeInput;

        if (cognome) {
            cognome.addEventListener("blur", function () {
                applyToInput(cognome, formatCognome);
            });
        }
        if (nome) {
            nome.addEventListener("blur", function () {
                applyToInput(nome, formatNome);
            });
        }
    }

    function formatFields(cognomeInput, nomeInput) {
        const cognome =
            cognomeInput ||
            document.getElementById("id_cognome") ||
            document.getElementById("id_referente_cognome");
        const nome =
            nomeInput ||
            document.getElementById("id_nome") ||
            document.getElementById("id_referente_nome");
        applyToInput(cognome, formatCognome);
        applyToInput(nome, formatNome);
    }

    window.LabRepairNameCase = {
        formatCognome: formatCognome,
        formatNome: formatNome,
        bind: bind,
        formatFields: formatFields,
    };
})(window);
