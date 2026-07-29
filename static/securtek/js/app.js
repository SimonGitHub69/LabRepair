function getCurrentTheme() {
    return document.documentElement.getAttribute("data-bs-theme") || "light";
}

function applyTheme(theme) {
    const normalizedTheme = theme === "dark" ? "dark" : "light";
    const toggleButton = document.querySelector("[data-theme-toggle]");
    const toggleIcon = document.querySelector("[data-theme-toggle-icon]");
    const label = normalizedTheme === "dark" ? "Attiva tema chiaro" : "Attiva tema scuro";

    document.documentElement.setAttribute("data-bs-theme", normalizedTheme);
    localStorage.setItem("labrepair-theme", normalizedTheme);
    localStorage.setItem("securtek-theme", normalizedTheme);

    if (toggleButton) {
        toggleButton.setAttribute("aria-label", label);
        toggleButton.setAttribute("title", label);
    }

    if (toggleIcon) {
        toggleIcon.classList.toggle("ti-moon", normalizedTheme !== "dark");
        toggleIcon.classList.toggle("ti-sun", normalizedTheme === "dark");
    }
}

function padDatePart(value) {
    return String(value).padStart(2, "0");
}

function todayIsoDate() {
    const now = new Date();
    return `${now.getFullYear()}-${padDatePart(now.getMonth() + 1)}-${padDatePart(now.getDate())}`;
}

function nowIsoDateTimeLocal() {
    const now = new Date();
    return `${now.getFullYear()}-${padDatePart(now.getMonth() + 1)}-${padDatePart(now.getDate())}T${padDatePart(now.getHours())}:${padDatePart(now.getMinutes())}`;
}

function initCurrentYearDateFields() {
    document.querySelectorAll('input[type="date"][data-current-year="true"]').forEach(function (field) {
        field.addEventListener("focus", function () {
            if (!field.value) {
                field.value = todayIsoDate();
            }
        });
    });

    document.querySelectorAll('input[type="datetime-local"][data-current-year="true"]').forEach(function (field) {
        field.addEventListener("focus", function () {
            if (!field.value) {
                field.value = nowIsoDateTimeLocal();
            }
        });
    });
}

function initCollapsibleSections() {
    function setSectionCollapsed(button, section, collapsed, persist) {
        section.hidden = collapsed;
        button.classList.toggle("is-collapsed", collapsed);
        button.setAttribute("aria-expanded", collapsed ? "false" : "true");
        button.title = collapsed ? "Espandi sezione" : "Comprimi sezione";

        if (persist && button.dataset.storageKey) {
            localStorage.setItem(button.dataset.storageKey, collapsed ? "1" : "0");
        }
    }

    document.querySelectorAll(".st-collapse-toggle").forEach(function (button) {
        if (button.dataset.collapseReady === "1") {
            return;
        }

        const section = document.getElementById(button.dataset.collapseTarget);
        if (!section) {
            return;
        }

        button.dataset.storageKey = [
            "labrepair",
            "collapse",
            window.location.pathname,
            button.dataset.collapseKey || button.dataset.collapseTarget,
        ].join(":");

        button.dataset.collapseReady = "1";
        setSectionCollapsed(
            button,
            section,
            localStorage.getItem(button.dataset.storageKey) === "1",
            false
        );

        button.addEventListener("click", function () {
            setSectionCollapsed(button, section, !section.hidden, true);
        });
    });

    if (window.location.hash === "#comunicazioni") {
        const panel = document.getElementById("practice-communications-panel");
        const toggle = document.querySelector(
            '[data-collapse-target="practice-communications-panel"], [data-collapse-target="practice-communications-section"]'
        );
        if (panel && toggle) {
            setSectionCollapsed(toggle, panel, false, true);
            document.getElementById("comunicazioni")?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }
}

function initComunicazioneDeleteConfirm() {
    document.querySelectorAll("form[data-comunicazione-delete]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            event.preventDefault();

            const ask = window.LabRepairConfirm
                ? window.LabRepairConfirm.ask({
                      title: "Elimina comunicazione",
                      message: "Vuoi eliminare questa comunicazione?",
                      confirmLabel: "Elimina",
                      cancelLabel: "Annulla",
                      confirmClass: "btn btn-danger",
                      variant: "danger",
                  })
                : Promise.resolve(window.confirm("Vuoi eliminare questa comunicazione?"));

            ask.then(function (confirmed) {
                if (confirmed) {
                    form.submit();
                }
            });
        });
    });
}

function initPraticaDeleteConfirm() {
    const modalElement = document.getElementById("deletePraticaModal");
    const form = document.getElementById("deletePraticaForm");
    const nameElement = document.getElementById("deletePraticaName");
    const cancelButton = modalElement
        ? modalElement.querySelector(".js-delete-pratica-cancel")
        : null;

    if (!modalElement || !form || !nameElement || !cancelButton) {
        return;
    }

    function closeModal() {
        modalElement.hidden = true;
        document.body.classList.remove("st-confirm-open");
        form.removeAttribute("action");
    }

    function openModal(action, name) {
        form.action = action || "";
        nameElement.textContent = name || "Riparazione selezionata";
        modalElement.hidden = false;
        document.body.classList.add("st-confirm-open");
    }

    document.querySelectorAll(".js-delete-pratica").forEach(function (button) {
        button.addEventListener("click", function () {
            openModal(button.dataset.deleteAction, button.dataset.deleteName);
        });
    });

    cancelButton.addEventListener("click", closeModal);

    modalElement.addEventListener("click", function (event) {
        if (event.target === modalElement) {
            closeModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modalElement.hidden) {
            closeModal();
        }
    });
}

function disableBrowserFieldSuggestions(root) {
    const scope = root && root.querySelectorAll ? root : document;
    const guardedTypes = {
        text: true,
        search: true,
        email: true,
        tel: true,
        url: true,
        number: true,
        password: true,
        date: true,
        "datetime-local": true,
        time: true,
        month: true,
        week: true,
    };

    function opaqueFieldName() {
        return "f" + Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
    }

    function restoreFieldNames(form) {
        if (!form) {
            return;
        }
        form.querySelectorAll("[data-real-name]").forEach(function (field) {
            field.setAttribute("name", field.dataset.realName);
        });
    }

    function rescrambleFieldNames(form) {
        if (!form) {
            return;
        }
        form.querySelectorAll("[data-real-name]").forEach(function (field) {
            field.setAttribute("name", opaqueFieldName());
            field.setAttribute("autocomplete", "one-time-code");
        });
    }

    window.labrepairRestoreFormFieldNames = restoreFieldNames;
    window.labrepairRescrambleFormFieldNames = rescrambleFieldNames;

    function bindNameRestore(form) {
        if (form.dataset.nameRestoreBound === "1") {
            return;
        }
        form.dataset.nameRestoreBound = "1";
        form.addEventListener(
            "submit",
            function () {
                restoreFieldNames(form);
            },
            true
        );
        form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function (btn) {
            btn.addEventListener(
                "click",
                function () {
                    restoreFieldNames(form);
                },
                true
            );
        });
    }

    function injectAutofillDecoys(form) {
        if (!form || form.dataset.autofillDecoys === "1") {
            return;
        }
        form.dataset.autofillDecoys = "1";

        const wrap = document.createElement("div");
        wrap.setAttribute("aria-hidden", "true");
        wrap.style.cssText =
            "position:absolute;left:-10000px;top:auto;width:1px;height:1px;overflow:hidden;opacity:0;pointer-events:none;";

        [
            ["name", "text"],
            ["family-name", "text"],
            ["given-name", "text"],
            ["additional-name", "text"],
            ["email", "email"],
            ["tel", "tel"],
            ["tel-national", "tel"],
            ["street-address", "text"],
            ["address-line1", "text"],
            ["address-line2", "text"],
            ["postal-code", "text"],
            ["address-level1", "text"],
            ["address-level2", "text"],
            ["country-name", "text"],
            ["organization", "text"],
            ["cc-name", "text"],
        ].forEach(function (spec) {
            const input = document.createElement("input");
            input.type = spec[1];
            input.tabIndex = -1;
            input.autocomplete = spec[0];
            input.dataset.autofillDecoy = "1";
            wrap.appendChild(input);
        });

        form.insertBefore(wrap, form.firstChild);
    }

    scope.querySelectorAll("form").forEach(function (form) {
        form.setAttribute("autocomplete", "off");
        if (form.getAttribute("data-block-suggestions") === "1") {
            injectAutofillDecoys(form);
            bindNameRestore(form);
        }
    });

    scope.querySelectorAll("input, textarea, select").forEach(function (field) {
        if (field.type === "hidden" || field.type === "checkbox" || field.type === "radio" || field.type === "file") {
            return;
        }
        if (field.dataset.autofillDecoy === "1") {
            return;
        }

        const form = field.form || field.closest("form");
        const scrambleNames = !!(
            (form && form.getAttribute("data-block-suggestions") === "1") ||
            field.getAttribute("data-block-autofill") === "1"
        );

        if (scrambleNames && form) {
            bindNameRestore(form);
            injectAutofillDecoys(form);
            // Name completamente opaco: non deve contenere cognome/nome/email.
            const realName = field.getAttribute("name");
            if (realName && !field.dataset.realName) {
                field.dataset.realName = realName;
                field.setAttribute("name", opaqueFieldName());
            } else if (field.dataset.realName) {
                field.setAttribute("name", opaqueFieldName());
            }
        }

        field.setAttribute("autocomplete", scrambleNames ? "one-time-code" : "off");
        field.setAttribute("autocorrect", "off");
        field.setAttribute("autocapitalize", "off");
        field.setAttribute("spellcheck", "false");
        field.setAttribute("data-lpignore", "true");
        field.setAttribute("data-1p-ignore", "true");
        field.setAttribute("data-bwignore", "true");
        field.setAttribute("data-form-type", "other");

        if (field.hasAttribute("list")) {
            field.removeAttribute("list");
        }

        // type=email attiva l'autofill indirizzi di Chrome.
        if (scrambleNames && field.type === "email") {
            field.dataset.originalType = "email";
            field.type = "text";
            field.setAttribute("inputmode", "email");
        }

        if (
            (field.tagName === "TEXTAREA" || guardedTypes[field.type] || field.type === "" || field.dataset.originalType) &&
            field.dataset.autofillGuard !== "1"
        ) {
            field.dataset.autofillGuard = "1";
            field.setAttribute("readonly", "readonly");
            const unlock = function () {
                field.removeAttribute("readonly");
                if (scrambleNames) {
                    field.setAttribute("autocomplete", "one-time-code");
                    if (!field.dataset.realName && field.getAttribute("name")) {
                        field.dataset.realName = field.getAttribute("name");
                    }
                    if (field.dataset.realName) {
                        field.setAttribute("name", opaqueFieldName());
                    }
                }
            };
            field.addEventListener("focus", unlock);
            field.addEventListener("mousedown", unlock);
            field.addEventListener("touchstart", unlock, { passive: true });
        }
    });

    scope.querySelectorAll("datalist").forEach(function (list) {
        list.remove();
    });
}

var labrepairLeavingPage = false;
var labrepairClosingWindow = false;
var labrepairClosingTimer = null;
var labrepairSuppressUnloadPrompt = false;
var labrepairSuppressUnloadTimer = null;

function markLabRepairLeavingPage() {
    labrepairLeavingPage = true;
    labrepairClosingWindow = false;
    labrepairSuppressUnloadPrompt = false;
    if (labrepairClosingTimer) {
        window.clearTimeout(labrepairClosingTimer);
        labrepairClosingTimer = null;
    }
    if (labrepairSuppressUnloadTimer) {
        window.clearTimeout(labrepairSuppressUnloadTimer);
        labrepairSuppressUnloadTimer = null;
    }
}

function suppressLabRepairUnloadPrompt(durationMs) {
    // mailto/tel: non devono mostrare "Uscire dall'app?" ne' fare logout.
    labrepairSuppressUnloadPrompt = true;
    labrepairClosingWindow = false;
    if (labrepairSuppressUnloadTimer) {
        window.clearTimeout(labrepairSuppressUnloadTimer);
    }
    labrepairSuppressUnloadTimer = window.setTimeout(function () {
        labrepairSuppressUnloadPrompt = false;
        labrepairSuppressUnloadTimer = null;
    }, durationMs || 5000);
}

function isLabRepairLeavingPage() {
    return labrepairLeavingPage === true;
}

window.markLabRepairLeavingPage = markLabRepairLeavingPage;
window.suppressLabRepairUnloadPrompt = suppressLabRepairUnloadPrompt;

function sendLabRepairLogout(logoutUrl) {
    const silentUrl = logoutUrl + (logoutUrl.indexOf("?") >= 0 ? "&" : "?") + "silent=1";

    try {
        navigator.sendBeacon(silentUrl, "");
    } catch (error) {
        // sendBeacon non disponibile
    }

    try {
        fetch(silentUrl, {
            method: "GET",
            keepalive: true,
            credentials: "same-origin",
        }).catch(function () {
            // finestra in chiusura
        });
    } catch (error) {
        // fetch non disponibile
    }
}

function initLogoutOnClose() {
    if (document.body.dataset.logoutOnClose !== "1") {
        return;
    }

    const logoutUrl = document.body.dataset.logoutUrl || "/logout/";
    let sent = false;

    document.addEventListener("click", function (event) {
        const link = event.target.closest("a[href]");
        if (!link) {
            return;
        }

        const href = link.getAttribute("href");
        if (!href || href.charAt(0) === "#" || link.target === "_blank") {
            return;
        }
        if (/^(mailto:|tel:|javascript:)/i.test(href)) {
            suppressLabRepairUnloadPrompt(5000);
            return;
        }

        markLabRepairLeavingPage();
    }, true);

    document.addEventListener("submit", function (event) {
        const form = event.target;
        if (!form || form.tagName !== "FORM") {
            return;
        }
        if (form.hasAttribute("hx-post") || form.hasAttribute("hx-get")) {
            return;
        }
        if (form.querySelector("[hx-post], [hx-get]")) {
            return;
        }

        markLabRepairLeavingPage();
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "F5" || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "r")) {
            markLabRepairLeavingPage();
        }
    }, true);

    window.addEventListener("pageshow", function (event) {
        labrepairLeavingPage = false;
        labrepairClosingWindow = false;
        if (labrepairClosingTimer) {
            window.clearTimeout(labrepairClosingTimer);
            labrepairClosingTimer = null;
        }
    });

    window.addEventListener("beforeunload", function (event) {
        if (isLabRepairLeavingPage() || labrepairSuppressUnloadPrompt) {
            return;
        }

        labrepairClosingWindow = true;
        if (labrepairClosingTimer) {
            window.clearTimeout(labrepairClosingTimer);
        }
        labrepairClosingTimer = window.setTimeout(function () {
            labrepairClosingWindow = false;
            labrepairClosingTimer = null;
        }, 2000);

        event.preventDefault();
        event.returnValue = " ";
        return event.returnValue;
    });

    window.addEventListener("pagehide", function () {
        if (isLabRepairLeavingPage() || labrepairSuppressUnloadPrompt) {
            labrepairLeavingPage = false;
            return;
        }

        if (!labrepairClosingWindow) {
            return;
        }

        if (sent) {
            return;
        }

        sent = true;
        sendLabRepairLogout(logoutUrl);
    });
}

document.addEventListener("DOMContentLoaded", function () {
    initCurrentYearDateFields();
    initCollapsibleSections();
    initComunicazioneDeleteConfirm();
    initPraticaDeleteConfirm();
    initLogoutOnClose();
    disableBrowserFieldSuggestions(document);

    document.body.addEventListener("htmx:afterSwap", function (event) {
        disableBrowserFieldSuggestions(event.target || document);
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const toggleButton = document.querySelector("[data-sidebar-toggle]");
    const backdrop = document.querySelector("[data-sidebar-backdrop]");
    const sidebarNav = document.getElementById("stSidebarNav");
    const SCROLL_KEY = "labrepair-sidebar-scroll";

    function closeSidebar() {
        document.body.classList.remove("st-sidebar-open");
    }

    function saveSidebarScroll() {
        if (!sidebarNav) {
            return;
        }
        try {
            sessionStorage.setItem(SCROLL_KEY, String(sidebarNav.scrollTop));
        } catch (error) {
            // sessionStorage non disponibile
        }
    }

    function restoreSidebarScroll() {
        if (!sidebarNav) {
            return;
        }
        try {
            const saved = sessionStorage.getItem(SCROLL_KEY);
            if (saved !== null) {
                sidebarNav.scrollTop = parseInt(saved, 10) || 0;
                return true;
            }
        } catch (error) {
            // sessionStorage non disponibile
        }
        return false;
    }

    function ensureActiveVisibleIfNeeded() {
        if (!sidebarNav || restoreSidebarScroll()) {
            return;
        }

        const activeLink = sidebarNav.querySelector(".st-nav-link.active");
        if (!activeLink) {
            return;
        }

        const navRect = sidebarNav.getBoundingClientRect();
        const linkRect = activeLink.getBoundingClientRect();
        const topOverflow = linkRect.top - navRect.top;
        const bottomOverflow = linkRect.bottom - navRect.bottom;

        if (topOverflow < 0) {
            sidebarNav.scrollTop += topOverflow;
        } else if (bottomOverflow > 0) {
            sidebarNav.scrollTop += bottomOverflow;
        }
        saveSidebarScroll();
    }

    if (sidebarNav) {
        ensureActiveVisibleIfNeeded();

        sidebarNav.addEventListener(
            "scroll",
            function () {
                window.clearTimeout(sidebarNav._scrollSaveTimer);
                sidebarNav._scrollSaveTimer = window.setTimeout(saveSidebarScroll, 80);
            },
            { passive: true }
        );
    }

    if (toggleButton) {
        toggleButton.addEventListener("click", function () {
            document.body.classList.toggle("st-sidebar-open");
        });
    }

    if (backdrop) {
        backdrop.addEventListener("click", closeSidebar);
    }

    document.querySelectorAll(".st-sidebar .st-nav-link").forEach(function (link) {
        link.addEventListener("click", function () {
            saveSidebarScroll();
            if (window.matchMedia("(max-width: 991.98px)").matches) {
                closeSidebar();
            }
        });
    });

    window.addEventListener("pagehide", saveSidebarScroll);
});

document.addEventListener("DOMContentLoaded", function () {
    const toggleButton = document.querySelector("[data-theme-toggle]");

    applyTheme(getCurrentTheme());

    if (!toggleButton) {
        return;
    }

    toggleButton.addEventListener("click", function () {
        applyTheme(getCurrentTheme() === "dark" ? "light" : "dark");
    });
});
