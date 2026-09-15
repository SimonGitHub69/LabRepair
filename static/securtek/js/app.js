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

window.labrepairTodayIsoDate = todayIsoDate;

function syncConsegnaMinDate(root) {
    const scope = root && root.querySelectorAll ? root : document;
    const field =
        scope.querySelector("#id_data_scadenza") ||
        document.getElementById("id_data_scadenza");
    if (!(field instanceof HTMLInputElement) || field.type !== "date") {
        return;
    }

    const today = todayIsoDate();
    let min = today;
    const yearMin = field.getAttribute("data-date-min-year");
    if (yearMin) {
        const yearStart = String(yearMin).padStart(4, "0") + "-01-01";
        if (yearStart > min) {
            min = yearStart;
        }
    }

    field.setAttribute("data-min", min);
    field.removeAttribute("min");
    field.dataset.consegnaMinToday = today;
    field.setAttribute("data-consegna-not-before-today", "1");
}

function nowIsoDateTimeLocal() {
    const now = new Date();
    return `${now.getFullYear()}-${padDatePart(now.getMonth() + 1)}-${padDatePart(now.getDate())}T${padDatePart(now.getHours())}:${padDatePart(now.getMinutes())}`;
}

function formatIsoDateShortYear(isoValue) {
    return formatIsoDateDisplay(isoValue, false);
}

function formatIsoDateDisplay(isoValue, fullYear) {
    const match = String(isoValue || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!match) {
        return "";
    }
    const year = fullYear ? match[1] : match[1].slice(-2);
    return match[3] + "/" + match[2] + "/" + year;
}

function isFullYearDateField(nativeField) {
    return !!(
        nativeField &&
        (nativeField.getAttribute("data-date-year") === "full" ||
            nativeField.id === "id_data_nascita")
    );
}

function isBirthDateField(nativeField) {
    return isFullYearDateField(nativeField);
}

function ageInYearsFromIso(iso, todayIso) {
    const born = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    const today = String(todayIso || todayIsoDate()).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!born || !today) {
        return null;
    }
    let years = Number(today[1]) - Number(born[1]);
    if (today[2] + today[3] < born[2] + born[3]) {
        years -= 1;
    }
    return years;
}

function birthDateCoherenceMessage(nativeField, iso) {
    const today = todayIsoDate();
    if (iso > today) {
        return "La data di nascita non può essere successiva a oggi.";
    }
    const age = ageInYearsFromIso(iso, today);
    if (age == null) {
        return "";
    }
    const minAge = Number(nativeField.getAttribute("data-nascita-eta-min") || 6);
    const maxAge = Number(nativeField.getAttribute("data-nascita-eta-max") || 100);
    const limit = Number(nativeField.getAttribute("data-nascita-eta-limite") || 120);
    if (age > limit) {
        return "Data di nascita non valida: l'età risulterebbe superiore a " + limit + " anni.";
    }
    if (age > maxAge) {
        return "Controlla la data di nascita: l'età risulta di " + age + " anni (oltre " + maxAge + ").";
    }
    if (age < minAge) {
        const label = age <= 0 ? "meno di un anno" : age === 1 ? "1 anno" : age + " anni";
        return "Controlla la data di nascita: l'età risulta di " + label + " (inferiore a " + minAge + " anni).";
    }
    return "";
}

function expandBirthTwoDigitYear(yy) {
    const n = Number(yy);
    if (!Number.isFinite(n) || n < 0 || n > 99) {
        return null;
    }
    const now = new Date().getFullYear();
    const y19 = 1900 + n;
    const y20 = 2000 + n;
    if (y20 <= now && now - y20 <= 120) {
        return y20;
    }
    if (y19 <= now && now - y19 <= 120) {
        return y19;
    }
    return y20 <= now ? y20 : y19;
}

function expandTwoDigitYear(yy, minYear, maxYear) {
    const n = Number(yy);
    if (!Number.isFinite(n) || n < 0 || n > 99) {
        return null;
    }
    const y19 = 1900 + n;
    const y20 = 2000 + n;
    const minY = minYear != null && minYear !== "" ? Number(minYear) : null;
    const maxY = maxYear != null && maxYear !== "" ? Number(maxYear) : null;

    if (Number.isFinite(minY) && Number.isFinite(maxY)) {
        if (y20 >= minY && y20 <= maxY) {
            return y20;
        }
        if (y19 >= minY && y19 <= maxY) {
            return y19;
        }
    }

    const now = new Date().getFullYear();
    if (y20 <= now + 30) {
        return y20;
    }
    return y19;
}

function parseShortDateToIso(text, minYear, maxYear, options) {
    options = options || {};
    const raw = String(text || "").trim();
    if (!raw) {
        return "";
    }

    let match = raw.match(/^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{2}|\d{4})$/);
    if (!match) {
        const digits = raw.replace(/\D/g, "");
        if (digits.length === 6) {
            match = [null, digits.slice(0, 2), digits.slice(2, 4), digits.slice(4, 6)];
        } else if (digits.length === 8) {
            match = [null, digits.slice(0, 2), digits.slice(2, 4), digits.slice(4, 8)];
        } else {
            return null;
        }
    }

    const day = Number(match[1]);
    const month = Number(match[2]);
    let year = Number(match[3]);
    if (String(match[3]).length === 2) {
        year = options.birthYear
            ? expandBirthTwoDigitYear(match[3])
            : expandTwoDigitYear(match[3], minYear, maxYear);
    }
    if (!year || !month || !day || month < 1 || month > 12 || day < 1 || day > 31) {
        return null;
    }

    const iso =
        String(year) +
        "-" +
        padDatePart(month) +
        "-" +
        padDatePart(day);
    const probe = new Date(year, month - 1, day);
    if (
        probe.getFullYear() !== year ||
        probe.getMonth() !== month - 1 ||
        probe.getDate() !== day
    ) {
        return null;
    }
    return iso;
}

function formatShortDateInputMask(value, options) {
    options = options || {};
    const maxDigits = options.fullYear ? 8 : 6;
    const digits = String(value || "").replace(/\D/g, "").slice(0, maxDigits);
    if (!digits) {
        return "";
    }
    if (digits.length <= 2) {
        // Dopo giorno completo (2 cifre) mostra già lo slash.
        return options.pending && digits.length === 2 ? digits + "/" : digits;
    }
    if (digits.length <= 4) {
        const base = digits.slice(0, 2) + "/" + digits.slice(2);
        return options.pending && digits.length === 4 ? base + "/" : base;
    }
    return digits.slice(0, 2) + "/" + digits.slice(2, 4) + "/" + digits.slice(4);
}

function caretPosAfterDigits(masked, digitCount) {
    if (digitCount <= 0) {
        return 0;
    }
    let pos = 0;
    let seen = 0;
    while (pos < masked.length && seen < digitCount) {
        if (/\d/.test(masked.charAt(pos))) {
            seen += 1;
        }
        pos += 1;
    }
    // Se subito dopo c'è uno slash automatico, posiziona oltre.
    if (masked.charAt(pos) === "/") {
        pos += 1;
    }
    return pos;
}

function syncDateTextFromNative(nativeField, textField) {
    if (!nativeField || !textField) {
        return;
    }
    textField.value = formatIsoDateDisplay(nativeField.value, isFullYearDateField(nativeField));
    textField.classList.toggle("is-empty", !nativeField.value);
}

function getDateConstraint(nativeField, name) {
    if (!nativeField) {
        return "";
    }
    return (
        nativeField.getAttribute("data-" + name) ||
        nativeField.getAttribute(name) ||
        ""
    );
}

function isConsegnaDateField(nativeField) {
    return !!(
        nativeField &&
        (nativeField.id === "id_data_scadenza" ||
            nativeField.getAttribute("data-consegna-not-before-today") === "1" ||
            nativeField.dataset.consegnaMinToday)
    );
}

function applyTextDateToNative(nativeField, textField) {
    if (!nativeField || !textField) {
        return false;
    }
    const raw = String(textField.value || "").trim();
    if (!raw) {
        nativeField.value = "";
        textField.setCustomValidity("");
        syncDateTextFromNative(nativeField, textField);
        nativeField.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
    }

    const iso = parseShortDateToIso(
        raw,
        nativeField.getAttribute("data-date-min-year"),
        nativeField.getAttribute("data-date-max-year"),
        { birthYear: isFullYearDateField(nativeField) }
    );
    if (!iso) {
        textField.setCustomValidity(
            isFullYearDateField(nativeField)
                ? "Data non valida. Usa gg/mm/aaaa."
                : "Data non valida. Usa gg/mm/aa."
        );
        return false;
    }

    if (isBirthDateField(nativeField)) {
        const birthMessage = birthDateCoherenceMessage(nativeField, iso);
        if (birthMessage) {
            textField.setCustomValidity(birthMessage);
            return false;
        }
    }

    const minIso = getDateConstraint(nativeField, "min");
    const maxIso = getDateConstraint(nativeField, "max");
    if (minIso && iso < minIso) {
        textField.setCustomValidity(
            isConsegnaDateField(nativeField)
                ? "La data prevista consegna non può essere precedente a oggi."
                : isBirthDateField(nativeField)
                  ? "La data di nascita non è coerente. Controlla l'anno."
                  : "La data deve essere " +
                    formatIsoDateDisplay(minIso, isFullYearDateField(nativeField)) +
                    " o successiva."
        );
        return false;
    }
    if (maxIso && iso > maxIso) {
        textField.setCustomValidity(
            isBirthDateField(nativeField)
                ? "La data di nascita non può essere successiva a oggi."
                : "La data deve essere " +
                  formatIsoDateDisplay(maxIso, isFullYearDateField(nativeField)) +
                  " o precedente."
        );
        return false;
    }

    textField.setCustomValidity("");
    nativeField.value = iso;
    syncDateTextFromNative(nativeField, textField);
    nativeField.dispatchEvent(new Event("input", { bubbles: true }));
    nativeField.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
}

function applyDatePickerBounds(field) {
    if (!(field instanceof HTMLInputElement)) {
        return;
    }
    // Autofill-guard può lasciare readonly: showPicker fallirebbe (immutable).
    if (field.dataset.autofillGuard === "1") {
        field.removeAttribute("readonly");
    }
    const dataMin = field.getAttribute("data-min");
    const dataMax = field.getAttribute("data-max");
    if (dataMin) {
        field.setAttribute("min", dataMin);
    }
    if (dataMax) {
        field.setAttribute("max", dataMax);
    }
    field.dataset.datePickerOpen = "1";
}

function clearDatePickerBounds(field) {
    if (!(field instanceof HTMLInputElement)) {
        return;
    }
    field.removeAttribute("min");
    field.removeAttribute("max");
    delete field.dataset.datePickerOpen;
}

function isDatePickerOpen(field) {
    return !!(field && field.dataset && field.dataset.datePickerOpen === "1");
}

function openNativeDatePicker(field) {
    if (!(field instanceof HTMLInputElement) || field.disabled) {
        return;
    }
    applyDatePickerBounds(field);
    if (field.readOnly) {
        return;
    }
    try {
        if (typeof field.showPicker === "function") {
            field.showPicker();
            return;
        }
    } catch (error) {
        // showPicker può fallire senza gesture o se il controllo non è visibile
    }
    try {
        field.focus({ preventScroll: true });
        field.click();
    } catch (error) {
        // ignore
    }
}

function enhanceDateField(nativeField) {
    if (!(nativeField instanceof HTMLInputElement) || nativeField.type !== "date") {
        return;
    }
    if (nativeField.dataset.dateEnhanced === "1") {
        const text = nativeField.parentElement
            ? nativeField.parentElement.querySelector(".st-date-text")
            : null;
        if (text) {
            syncDateTextFromNative(nativeField, text);
        }
        return;
    }

    let wrap = nativeField.closest(".st-date-field");
    if (!wrap) {
        wrap = document.createElement("span");
        wrap.className = "st-date-field";
        nativeField.parentNode.insertBefore(wrap, nativeField);
        wrap.appendChild(nativeField);
    }

    nativeField.classList.add("st-date-native");
    nativeField.tabIndex = -1;
    nativeField.setAttribute("tabindex", "-1");
    nativeField.setAttribute("aria-hidden", "true");

    // Evita i popup HTML5 del date nascosto (es. "Il valore deve essere 08/09/2026...").
    // I limiti restano in data-* e li controlliamo noi sul campo testo.
    if (nativeField.getAttribute("min") && !nativeField.getAttribute("data-min")) {
        nativeField.setAttribute("data-min", nativeField.getAttribute("min"));
    }
    if (nativeField.getAttribute("max") && !nativeField.getAttribute("data-max")) {
        nativeField.setAttribute("data-max", nativeField.getAttribute("max"));
    }
    if (nativeField.required) {
        nativeField.setAttribute("data-required", "1");
        nativeField.required = false;
    }
    nativeField.removeAttribute("min");
    nativeField.removeAttribute("max");

    nativeField.addEventListener("invalid", function (event) {
        event.preventDefault();
    });

    let textField = wrap.querySelector(".st-date-text");
    if (!textField) {
        textField = document.createElement("input");
        textField.type = "text";
        textField.className = "form-control st-date-text";
        if (nativeField.classList.contains("form-control-sm")) {
            textField.classList.add("form-control-sm");
        }
        textField.inputMode = "numeric";
        textField.autocomplete = "off";
        textField.placeholder = isFullYearDateField(nativeField) ? "gg/mm/aaaa" : "gg/mm/aa";
        textField.spellcheck = false;
        textField.maxLength = isFullYearDateField(nativeField) ? 10 : 8;
        if (nativeField.disabled) {
            textField.disabled = true;
        }
        if (nativeField.readOnly) {
            textField.readOnly = true;
        }
        wrap.insertBefore(textField, nativeField);
    }
    textField.placeholder = isFullYearDateField(nativeField) ? "gg/mm/aaaa" : "gg/mm/aa";
    textField.maxLength = isFullYearDateField(nativeField) ? 10 : 8;

    let btn = wrap.querySelector(".st-date-calendar-btn");
    if (!btn) {
        btn = document.createElement("button");
        btn.type = "button";
        btn.className = "st-date-calendar-btn";
        btn.tabIndex = -1;
        btn.setAttribute("tabindex", "-1");
        btn.setAttribute("aria-hidden", "true");
        btn.title = "Apri calendario";
        btn.innerHTML = '<i class="ti ti-calendar" aria-hidden="true"></i>';
        wrap.appendChild(btn);
    }

    syncDateTextFromNative(nativeField, textField);

    if (nativeField.id) {
        const label = document.querySelector('label[for="' + nativeField.id + '"]');
        if (label) {
            const textId = nativeField.id + "__display";
            textField.id = textId;
            label.setAttribute("for", textId);
        }
    }

    textField.addEventListener("focus", function () {
        window.requestAnimationFrame(function () {
            textField.select();
        });
    });

    textField.addEventListener("keydown", function (event) {
        // I separatori li mette la maschera: non digitarli.
        if (event.key === "/" || event.key === "." || event.key === "-") {
            event.preventDefault();
            return;
        }
        if (event.key === "Enter") {
            const ok = applyTextDateToNative(nativeField, textField);
            if (!ok && isConsegnaDateField(nativeField)) {
                event.preventDefault();
                textField.reportValidity();
            }
        }
    });

    textField.addEventListener("input", function () {
        const before = textField.value;
        const start = typeof textField.selectionStart === "number" ? textField.selectionStart : before.length;
        const digitsBefore = before.slice(0, start).replace(/\D/g, "").length;
        const masked = formatShortDateInputMask(before, {
            pending: true,
            fullYear: isFullYearDateField(nativeField),
        });
        if (masked !== before) {
            textField.value = masked;
        }
        const pos = caretPosAfterDigits(textField.value, digitsBefore);
        try {
            textField.setSelectionRange(pos, pos);
        } catch (error) {
            // ignore
        }
        textField.setCustomValidity("");
    });

    textField.addEventListener("blur", function () {
        // In uscita normalizza senza slash finali pendenti.
        textField.value = formatShortDateInputMask(textField.value, {
            pending: false,
            fullYear: isFullYearDateField(nativeField),
        });
        const ok = applyTextDateToNative(nativeField, textField);
        // Consegna / nascita: messaggio subito in uscita dal campo.
        // Differisci: se il blur è per Annulla/Salva, non rubare il click.
        if (
            !ok &&
            String(textField.value || "").trim() &&
            (isConsegnaDateField(nativeField) || isBirthDateField(nativeField))
        ) {
            window.setTimeout(function () {
                const active = document.activeElement;
                if (
                    active &&
                    active.closest(
                        "[data-pratica-annulla], [data-pratica-salva], [data-embed-close], button[type='submit'], a[href]"
                    )
                ) {
                    return;
                }
                textField.reportValidity();
            }, 0);
        }
    });

    // keydown Enter gestito sopra; evita listener duplicato.

    function preparePickerOpen() {
        applyDatePickerBounds(nativeField);
    }

    nativeField.addEventListener("pointerdown", preparePickerOpen);
    btn.addEventListener("pointerdown", preparePickerOpen);

    nativeField.addEventListener("blur", function () {
        window.setTimeout(function () {
            if (document.activeElement === nativeField) {
                return;
            }
            const wasOpen = isDatePickerOpen(nativeField);
            clearDatePickerBounds(nativeField);
            if (
                wasOpen &&
                textField &&
                !textField.disabled &&
                (document.activeElement === document.body ||
                    document.activeElement === document.documentElement)
            ) {
                textField.focus({ preventScroll: true });
            }
        }, 0);
    });

    btn.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        openNativeDatePicker(nativeField);
    });

    function rejectPastConsegnaFromNative() {
        if (!isConsegnaDateField(nativeField)) {
            textField.setCustomValidity("");
            return true;
        }
        const minIso = getDateConstraint(nativeField, "min") || todayIsoDate();
        const value = String(nativeField.value || "").trim();
        if (value && value < minIso) {
            nativeField.value = "";
            syncDateTextFromNative(nativeField, textField);
            textField.setCustomValidity(
                "La data prevista consegna non può essere precedente a oggi."
            );
            textField.reportValidity();
            return false;
        }
        textField.setCustomValidity("");
        return true;
    }

    nativeField.addEventListener("change", function () {
        syncDateTextFromNative(nativeField, textField);
        if (isConsegnaDateField(nativeField)) {
            rejectPastConsegnaFromNative();
            return;
        }
        if (isBirthDateField(nativeField)) {
            const iso = String(nativeField.value || "").trim();
            if (!iso) {
                textField.setCustomValidity("");
                return;
            }
            const msg = birthDateCoherenceMessage(nativeField, iso);
            textField.setCustomValidity(msg || "");
            if (msg) {
                textField.reportValidity();
            }
            return;
        }
        textField.setCustomValidity("");
    });
    nativeField.addEventListener("input", function () {
        syncDateTextFromNative(nativeField, textField);
    });

    // Se JS imposta .value sul native (es. documento), aggiorna il testo.
    const valueDescriptor = Object.getOwnPropertyDescriptor(
        HTMLInputElement.prototype,
        "value"
    );
    if (valueDescriptor && valueDescriptor.set && !nativeField.dataset.dateValuePatched) {
        nativeField.dataset.dateValuePatched = "1";
        Object.defineProperty(nativeField, "value", {
            configurable: true,
            enumerable: true,
            get: function () {
                return valueDescriptor.get.call(this);
            },
            set: function (next) {
                valueDescriptor.set.call(this, next);
                syncDateTextFromNative(nativeField, textField);
            },
        });
    }

    // disabled sync
    const disabledDescriptor = Object.getOwnPropertyDescriptor(
        HTMLInputElement.prototype,
        "disabled"
    );
    if (disabledDescriptor && disabledDescriptor.set && !nativeField.dataset.dateDisabledPatched) {
        nativeField.dataset.dateDisabledPatched = "1";
        Object.defineProperty(nativeField, "disabled", {
            configurable: true,
            enumerable: true,
            get: function () {
                return disabledDescriptor.get.call(this);
            },
            set: function (next) {
                disabledDescriptor.set.call(this, next);
                textField.disabled = !!next;
            },
        });
    }

    nativeField.dataset.dateEnhanced = "1";
    nativeField.dataset.shortYearBound = "1";
    nativeField.dataset.calendarBtnBound = "1";
}

function initShortYearDateFields(root) {
    const scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll('input[type="date"]').forEach(function (field) {
        enhanceDateField(field);
    });
}

window.labrepairSyncShortYearDates = initShortYearDateFields;

function commitDateFields(root) {
    const scope = root && root.querySelectorAll ? root : document;
    let ok = true;
    scope.querySelectorAll(".st-date-field").forEach(function (wrap) {
        const nativeField = wrap.querySelector('input[type="date"].st-date-native, input[type="date"]');
        const textField = wrap.querySelector(".st-date-text");
        if (!nativeField || !textField) {
            return;
        }
        if (!applyTextDateToNative(nativeField, textField)) {
            ok = false;
            if (typeof textField.reportValidity === "function") {
                textField.reportValidity();
            }
        }
    });
    return ok;
}

window.labrepairCommitDateFields = commitDateFields;

function initCurrentYearDateFields() {
    document.querySelectorAll('input[type="date"][data-current-year="true"]').forEach(function (field) {
        field.addEventListener("focus", function () {
            if (!field.value) {
                field.value = todayIsoDate();
            }
        });
        const wrap = field.closest(".st-date-field");
        const text = wrap ? wrap.querySelector(".st-date-text") : null;
        if (text) {
            text.addEventListener("focus", function () {
                if (!field.value && !String(text.value || "").trim()) {
                    field.value = todayIsoDate();
                    syncDateTextFromNative(field, text);
                }
            });
        }
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
        const summaryMode = button.dataset.collapseMode === "summary";
        const full = section.querySelector("[data-com-full]");
        const summary = section.querySelector("[data-com-riepilogo]");

        if (summaryMode && (full || summary)) {
            // Note e Comunicazioni: Chiudi → riepilogo; Espandi → vista completa aperta.
            section.hidden = false;
            section.removeAttribute("hidden");
            section.classList.toggle("is-riepilogo", collapsed);

            if (full) {
                if (collapsed) {
                    full.setAttribute("hidden", "");
                    full.hidden = true;
                } else {
                    // Espandi: forza tutta la sezione aperta (form + elenco completo).
                    full.hidden = false;
                    full.removeAttribute("hidden");
                    full.style.removeProperty("display");
                }
            }
            if (summary) {
                if (collapsed) {
                    summary.hidden = false;
                    summary.removeAttribute("hidden");
                    summary.querySelectorAll("details[data-com-day]").forEach(function (day) {
                        day.open = true;
                    });
                } else {
                    summary.hidden = true;
                    summary.setAttribute("hidden", "");
                }
            }
        } else {
            section.hidden = collapsed;
            section.classList.remove("is-riepilogo");
        }

        button.classList.toggle("is-collapsed", collapsed);
        button.setAttribute("aria-expanded", collapsed ? "false" : "true");
        button.title = collapsed
            ? summaryMode
                ? "Apri elenco completo"
                : "Espandi sezione"
            : summaryMode
              ? "Mostra riepilogo per data"
              : "Comprimi sezione";

        const label = button.querySelector("[data-collapse-label]");
        if (label) {
            label.textContent = collapsed
                ? summaryMode
                    ? "Espandi"
                    : "Apri"
                : "Chiudi";
        }

        if (persist && button.dataset.storageKey) {
            localStorage.setItem(button.dataset.storageKey, collapsed ? "1" : "0");
        }
    }

    window.labrepairSetSectionCollapsed = function (targetId, collapsed, persist) {
        const button = document.querySelector(
            '.st-collapse-toggle[data-collapse-target="' + targetId + '"]'
        );
        const section = document.getElementById(targetId);
        if (!button || !section) {
            return;
        }
        setSectionCollapsed(button, section, !!collapsed, !!persist);
    };

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

        // data-collapse-default="open" → sempre aperta all'ingresso (es. Note e Comunicazioni).
        let collapsed = localStorage.getItem(button.dataset.storageKey) === "1";
        if (button.dataset.collapseDefault === "open") {
            collapsed = false;
        } else if (button.dataset.collapseDefault === "collapsed") {
            collapsed = true;
        }

        setSectionCollapsed(button, section, collapsed, false);

        button.addEventListener("click", function () {
            // Usa aria-expanded come stato affidabile (vista completa vs riepilogo).
            const currentlyCollapsed = button.getAttribute("aria-expanded") === "false";
            setSectionCollapsed(button, section, !currentlyCollapsed, true);
        });
    });

    if (window.location.hash === "#comunicazioni") {
        const panel =
            document.getElementById("practice-communications-panel") ||
            document.getElementById("practice-communications-section");
        const toggle = document.querySelector(
            '[data-collapse-target="practice-communications-panel"], [data-collapse-target="practice-communications-section"]'
        );
        if (panel && toggle) {
            setSectionCollapsed(toggle, panel, false, true);
            (
                document.getElementById("comunicazioni") || panel.closest(".card")
            )?.scrollIntoView({ behavior: "smooth", block: "start" });
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
        // date/datetime/time restano editabili: readonly blocca showPicker.
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

        const skipReadonlyGuard =
            field.classList.contains("st-date-native") ||
            field.type === "date" ||
            field.type === "datetime-local" ||
            field.type === "time" ||
            field.type === "month" ||
            field.type === "week";

        if (
            !skipReadonlyGuard &&
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

function patchLabRepairNavigationGuards() {
    // Intercetta navigazioni JS (location.assign/reload, form.submit nativo)
    // che non passano dai listener click/submit. Senza questo, in modalità App
    // beforeunload tratta il cambio pagina come chiusura e fa logout.
    function isSameDocumentUrl(url) {
        if (url == null || url === "") {
            return false;
        }
        try {
            const nextUrl = new URL(String(url), window.location.href);
            return (
                nextUrl.origin === window.location.origin &&
                nextUrl.pathname === window.location.pathname &&
                nextUrl.search === window.location.search
            );
        } catch (error) {
            return false;
        }
    }

    function wrapLocationNav(name) {
        try {
            const original = window.location[name];
            if (typeof original !== "function" || original._labrepairNavWrapped) {
                return;
            }
            const wrapped = function (url) {
                if (name === "reload" || !isSameDocumentUrl(url)) {
                    markLabRepairLeavingPage();
                }
                return original.apply(window.location, arguments);
            };
            wrapped._labrepairNavWrapped = true;
            window.location[name] = wrapped;
        } catch (error) {
            // location non patchabile
        }
    }

    wrapLocationNav("assign");
    wrapLocationNav("replace");
    wrapLocationNav("reload");

    try {
        const originalSubmit = HTMLFormElement.prototype.submit;
        if (typeof originalSubmit === "function" && !originalSubmit._labrepairNavWrapped) {
            const wrappedSubmit = function () {
                markLabRepairLeavingPage();
                return originalSubmit.apply(this, arguments);
            };
            wrappedSubmit._labrepairNavWrapped = true;
            HTMLFormElement.prototype.submit = wrappedSubmit;
        }
    } catch (error) {
        // submit non patchabile
    }

    if (window.navigation && typeof window.navigation.addEventListener === "function") {
        window.navigation.addEventListener("navigate", function (event) {
            if (event.hashChange || event.downloadRequest) {
                return;
            }
            const dest = event.destination;
            if (dest && dest.sameDocument) {
                return;
            }
            markLabRepairLeavingPage();
        });
    }
}

function initLogoutOnClose() {
    if (document.body.dataset.logoutOnClose !== "1") {
        return;
    }

    const logoutUrl = document.body.dataset.logoutUrl || "/logout/";
    let sent = false;
    const hasNavigationApi =
        window.navigation && typeof window.navigation.addEventListener === "function";

    patchLabRepairNavigationGuards();

    document.addEventListener("click", function (event) {
        const link = event.target.closest("a[href], a[data-st-nav-href]");
        if (!link) {
            return;
        }

        const href = link.getAttribute("href") || link.dataset.stNavHref || "";
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

    // F5/Ctrl+R: solo se manca Navigation API. Con l'API il reload arriva
    // come navigate; marcare F5 in capture faceva "uscita" anche quando F5
    // è scorciatoia Salva (preventDefault successivo).
    if (!hasNavigationApi) {
        document.addEventListener("keydown", function (event) {
            if (event.key === "F5" || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "r")) {
                markLabRepairLeavingPage();
            }
        }, true);
    }

    window.addEventListener("beforeprint", function () {
        suppressLabRepairUnloadPrompt(120000);
    });
    window.addEventListener("afterprint", function () {
        suppressLabRepairUnloadPrompt(2000);
    });

    window.addEventListener("pageshow", function () {
        sent = false;
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

    window.addEventListener("pagehide", function (event) {
        if (event.persisted) {
            labrepairClosingWindow = false;
            return;
        }

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

function getFormActionsBottomInset() {
    const actions = document.querySelector(".st-form-actions");
    if (!actions) {
        return 28;
    }
    const rect = actions.getBoundingClientRect();
    // Barra sticky in basso: spazio occupato fino al fondo viewport + margine.
    const fromBottom = window.innerHeight - rect.top + 16;
    if (fromBottom > 48 && fromBottom < window.innerHeight * 0.55) {
        return fromBottom;
    }
    return Math.max(72, (actions.offsetHeight || 56) + 28);
}

function ensureElementInViewport(el, options) {
    options = options || {};
    if (!el || !(el instanceof Element)) {
        return;
    }

    // Se il focus è finito sul date nativo (invisibile), passa al testo.
    // Non rubare il focus mentre il calendario nativo è aperto.
    if (el.classList && el.classList.contains("st-date-native")) {
        if (isDatePickerOpen(el)) {
            return;
        }
        const wrapNative = el.closest(".st-date-field");
        const textNative = wrapNative ? wrapNative.querySelector(".st-date-text") : null;
        if (textNative) {
            el = textNative;
            if (document.activeElement !== textNative) {
                textNative.focus({ preventScroll: true });
            }
        }
    }

    // Campi data: scrolla il testo visibile, non l'input nativo nascosto.
    const dateWrap = el.closest(".st-date-field");
    if (dateWrap) {
        const text = dateWrap.querySelector(".st-date-text");
        if (text) {
            el = text;
        }
    }

    // Preferisci il blocco campo (label + input) così Cognome non resta tagliato.
    const fieldBlock =
        el.closest(".mb-3, .st-anagrafica-fact, .st-cliente-search-field, .st-date-field") || el;

    // Sblocco difensivo: dopo dialog "documento scaduto" a volte resta overflow hidden.
    if (document.body.classList.contains("st-confirm-open")) {
        const openConfirm = document.querySelector(".st-confirm:not([hidden])");
        if (!openConfirm) {
            document.body.classList.remove("st-confirm-open");
        }
    }

    const behavior = options.behavior || "auto";
    const navVar = getComputedStyle(document.documentElement).getPropertyValue("--st-navbar-height");
    const topPad = (parseFloat(navVar) || 52) + (options.topPad != null ? options.topPad : 16);
    const bottomPad =
        options.bottomPad != null ? options.bottomPad : getFormActionsBottomInset();

    function measureAndScroll() {
        if (!el.isConnected) {
            return;
        }
        const rect = fieldBlock.getBoundingClientRect();
        // Elemento invisibile / zero-size: non scrollare a vuoto.
        if (rect.width < 2 && rect.height < 2) {
            return;
        }
        const viewHeight = window.innerHeight;
        const visibleBottom = viewHeight - bottomPad;
        let delta = 0;

        if (rect.top < topPad) {
            delta = rect.top - topPad;
        } else if (rect.bottom > visibleBottom) {
            delta = rect.bottom - visibleBottom;
        }

        if (Math.abs(delta) > 2) {
            window.scrollBy({ top: delta, left: 0, behavior: behavior });
        }
    }

    function run() {
        measureAndScroll();
        if (options.remeasureMs) {
            window.setTimeout(measureAndScroll, options.remeasureMs);
        }
    }

    window.requestAnimationFrame(function () {
        window.requestAnimationFrame(run);
    });
}

window.labrepairEnsureInView = ensureElementInViewport;

function initKeyboardFocusScroll() {
    document.addEventListener("focusin", function (event) {
        const el = event.target;
        if (!(el instanceof HTMLElement)) {
            return;
        }
        if (el.closest(".st-sidebar, .st-confirm, .modal, [data-cliente-search-results]")) {
            return;
        }

        // Date nativo: non chiudere il calendario riportando il focus sul testo.
        if (el.classList.contains("st-date-native")) {
            if (isDatePickerOpen(el)) {
                return;
            }
            const wrap = el.closest(".st-date-field");
            const text = wrap ? wrap.querySelector(".st-date-text") : null;
            if (text && !text.disabled) {
                text.focus({ preventScroll: true });
                ensureElementInViewport(text, { behavior: "auto", remeasureMs: 80 });
            }
            return;
        }

        if (!el.matches("input, select, textarea, button:not([tabindex='-1']), a[href]:not([tabindex='-1'])")) {
            return;
        }
        if (el.classList.contains("st-date-calendar-btn")) {
            return;
        }

        // auto: con Tab rapido lo smooth fallisce, soprattutto dopo espansione documento scaduto.
        ensureElementInViewport(el, { behavior: "auto", remeasureMs: 120 });
    });
}

document.addEventListener("DOMContentLoaded", function () {
    initShortYearDateFields(document);
    syncConsegnaMinDate(document);
    initCurrentYearDateFields();
    initCollapsibleSections();
    initComunicazioneDeleteConfirm();
    initPraticaDeleteConfirm();
    initLogoutOnClose();
    initKeyboardFocusScroll();
    disableBrowserFieldSuggestions(document);

    document.body.addEventListener(
        "submit",
        function (event) {
            const form = event.target;
            if (!(form instanceof HTMLFormElement)) {
                return;
            }
            if (!commitDateFields(form)) {
                event.preventDefault();
                event.stopPropagation();
            }
        },
        true
    );

    document.body.addEventListener("htmx:afterSwap", function (event) {
        const target = event.target || document;
        disableBrowserFieldSuggestions(target);
        initShortYearDateFields(target);
        syncConsegnaMinDate(target);
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
            if (typeof window.markLabRepairLeavingPage === "function") {
                window.markLabRepairLeavingPage();
            }
            saveSidebarScroll();
            if (window.matchMedia("(max-width: 991.98px)").matches) {
                closeSidebar();
            }
        });
    });

    // Non rimuovere href al hover: in modalita' App faceva scattare "Uscire dall'app?"
    // sui click del menu. Il palloncino URL non compare comunque nella finestra --app.

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
