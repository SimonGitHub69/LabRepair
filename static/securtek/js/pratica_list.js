(function () {
    function getCsrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (match) {
            return decodeURIComponent(match[1]);
        }
        const input = document.querySelector("[name=csrfmiddlewaretoken]");
        return input ? input.value : "";
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function showListFlash(message, isError) {
        let flash = document.getElementById("stPraticaListFlash");
        if (!flash) {
            flash = document.createElement("div");
            flash.id = "stPraticaListFlash";
            flash.className = "alert mb-3";
            const anchor = document.querySelector(".st-pratica-list-card");
            if (anchor && anchor.parentNode) {
                anchor.parentNode.insertBefore(flash, anchor);
            } else {
                document.body.prepend(flash);
            }
        }
        flash.className = isError ? "alert alert-danger mb-3" : "alert alert-success mb-3";
        flash.textContent = message;
        window.clearTimeout(flash._hideTimer);
        flash._hideTimer = window.setTimeout(function () {
            flash.remove();
        }, 5000);
    }

    function initPraticaListFilters() {
        const form = document.querySelector(".st-pratica-filter-card form");
        if (!form) {
            return;
        }

        form.querySelectorAll("select").forEach(function (select) {
            select.addEventListener("change", function () {
                form.requestSubmit();
            });
        });
    }

    function initPraticaListRows() {
        document.querySelectorAll(".st-pratica-list-item").forEach(function (row) {
            row.style.cursor = "pointer";
            row.addEventListener("click", function (event) {
                if (event.target.closest("a, button")) {
                    return;
                }
                const link = row.querySelector(".st-pratica-codice");
                if (link) {
                    if (typeof window.markLabRepairLeavingPage === "function") {
                        window.markLabRepairLeavingPage();
                    }
                    window.location.href = link.href;
                }
            });
        });
    }

    function registerMailtoComunicazione(url) {
        return fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCsrfToken(),
                Accept: "application/json",
            },
            credentials: "same-origin",
        }).then(function (response) {
            return response.json().then(function (data) {
                return { ok: response.ok && data.ok, message: data.message || "" };
            });
        });
    }

    function openMailClient(href) {
        const tempLink = document.createElement("a");
        tempLink.href = href;
        tempLink.style.display = "none";
        tempLink.setAttribute("rel", "noopener");
        document.body.appendChild(tempLink);
        tempLink.click();
        tempLink.remove();
    }

    function initMailtoRegister() {
        document.querySelectorAll("[data-mailto-register]").forEach(function (link) {
            link.addEventListener("click", function (event) {
                const href = link.getAttribute("href") || "";
                const registerUrl = link.getAttribute("data-register-url") || "";
                if (!href || !registerUrl) {
                    return;
                }

                event.preventDefault();
                event.stopPropagation();
                if (typeof window.suppressLabRepairUnloadPrompt === "function") {
                    window.suppressLabRepairUnloadPrompt(5000);
                }
                openMailClient(href);

                window.setTimeout(function () {
                    const cliente = escapeHtml(link.getAttribute("data-cliente") || "cliente");
                    const ask = window.LabRepairConfirm
                        ? window.LabRepairConfirm.ask({
                              title: "Registra comunicazione",
                              message:
                                  "Vuoi registrare l&apos;invio della mail a " +
                                  "<span class=\"st-confirm-name\">" +
                                  cliente +
                                  "</span> nella sezione Comunicazioni della riparazione?",
                              confirmLabel: "Sì, registra",
                              cancelLabel: "No",
                              variant: "info",
                          })
                        : Promise.resolve(
                              window.confirm(
                                  "Vuoi registrare l'invio della mail nella sezione Comunicazioni?"
                              )
                          );

                    ask.then(function (confirmed) {
                        if (!confirmed) {
                            return;
                        }
                        registerMailtoComunicazione(registerUrl)
                            .then(function (result) {
                                showListFlash(
                                    result.message ||
                                        (result.ok
                                            ? "Comunicazione registrata."
                                            : "Registrazione non riuscita."),
                                    !result.ok
                                );
                                if (result.ok) {
                                    const openLink = link
                                        .closest(".st-pratica-list-item")
                                        ?.querySelector(".st-pratica-codice");
                                    if (openLink && openLink.href) {
                                        const flash = document.getElementById("stPraticaListFlash");
                                        if (flash) {
                                            const view = document.createElement("a");
                                            view.href = openLink.href + "#comunicazioni";
                                            view.className = "alert-link ms-2";
                                            view.textContent = "Apri riparazione";
                                            flash.appendChild(view);
                                        }
                                    }
                                }
                            })
                            .catch(function () {
                                showListFlash(
                                    "Errore durante la registrazione della comunicazione.",
                                    true
                                );
                            });
                    });
                }, 350);
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initPraticaListFilters();
        initPraticaListRows();
        initMailtoRegister();
    });
})();
