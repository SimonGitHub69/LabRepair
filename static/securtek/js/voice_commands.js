(function () {
    "use strict";

    function ready(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn);
        } else {
            fn();
        }
    }

    function normalize(text) {
        return String(text || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9\s]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function loadCommandMap() {
        var el = document.getElementById("labrepair-voice-commands");
        if (!el) {
            return {};
        }
        try {
            var raw = JSON.parse(el.textContent || "{}");
            var map = {};
            Object.keys(raw || {}).forEach(function (key) {
                var list = Array.isArray(raw[key]) ? raw[key] : [];
                map[key] = list
                    .map(normalize)
                    .filter(Boolean)
                    .sort(function (a, b) {
                        return b.length - a.length;
                    });
            });
            return map;
        } catch (err) {
            return {};
        }
    }

    function loadExtraCommands() {
        var el = document.getElementById("labrepair-voice-extra");
        if (!el) {
            return [];
        }
        try {
            var raw = JSON.parse(el.textContent || "[]");
            if (!Array.isArray(raw)) {
                return [];
            }
            return raw
                .map(function (item) {
                    var phrases = Array.isArray(item.frasi) ? item.frasi : [];
                    return {
                        phrases: phrases
                            .map(normalize)
                            .filter(Boolean)
                            .sort(function (a, b) {
                                return b.length - a.length;
                            }),
                        destinazione: item.destinazione || "",
                        url: item.url || "",
                        etichetta: item.etichetta || "",
                    };
                })
                .filter(function (item) {
                    return item.phrases.length > 0;
                });
        } catch (err) {
            return [];
        }
    }

    function phrases(map, key) {
        return map[key] || [];
    }

    function matchesExactOrIncludes(text, list) {
        for (var i = 0; i < list.length; i += 1) {
            var phrase = list[i];
            if (!phrase) {
                continue;
            }
            if (text === phrase || text.indexOf(phrase) !== -1) {
                return true;
            }
        }
        return false;
    }

    function matchPrefix(text, list) {
        for (var i = 0; i < list.length; i += 1) {
            var phrase = list[i];
            if (!phrase) {
                continue;
            }
            if (text === phrase) {
                return { matched: true, rest: "" };
            }
            if (text.indexOf(phrase + " ") === 0) {
                return { matched: true, rest: text.slice(phrase.length).trim() };
            }
        }
        return { matched: false, rest: "" };
    }

    function toast(message, isError) {
        var existing = document.getElementById("stVoiceToast");
        if (existing) {
            existing.remove();
        }
        var el = document.createElement("div");
        el.id = "stVoiceToast";
        el.className = "st-voice-toast" + (isError ? " is-error" : "");
        el.setAttribute("role", "status");
        el.textContent = message;
        document.body.appendChild(el);
        window.setTimeout(function () {
            el.classList.add("is-hide");
            window.setTimeout(function () {
                el.remove();
            }, 280);
        }, 3200);
    }

    function go(url) {
        if (!url) {
            return false;
        }
        if (typeof window.markLabRepairLeavingPage === "function") {
            window.markLabRepairLeavingPage();
        }
        window.location.href = url;
        return true;
    }

    function clickIfPresent(selector) {
        var el = document.querySelector(selector);
        if (el && el.tagName === "A" && el.getAttribute("href")) {
            if (typeof window.markLabRepairLeavingPage === "function") {
                window.markLabRepairLeavingPage();
            }
            window.location.href = el.getAttribute("href");
            return true;
        }
        return false;
    }

    function search(query, preferred) {
        var q = (query || "").trim();
        if (!q) {
            return false;
        }
        preferred = preferred || "";

        // Se siamo già su una lista con campo ricerca e non è forzata un'altra destinazione,
        // usa il form della pagina corrente.
        if (!preferred) {
            var input = document.querySelector("form[method='get'] input[name='q']");
            var form = input && input.form;
            if (form && input) {
                input.value = q;
                form.submit();
                return true;
            }
        }

        var urls = window.labrepairVoiceUrls || {};
        var base =
            (preferred === "anagrafiche" && urls.anagrafiche) ||
            (preferred === "riparazioni" && urls.riparazioni) ||
            urls.riparazioni ||
            urls.anagrafiche;
        if (!base) {
            return false;
        }
        var target = new URL(base, window.location.origin);
        target.searchParams.set("q", q);
        window.location.href = target.toString();
        return true;
    }

    function resolveDestination(destinazione, customUrl) {
        var urls = window.labrepairVoiceUrls || {};
        if (destinazione === "url") {
            return customUrl || "";
        }
        if (destinazione === "nuova_riparazione") {
            return urls.nuova_riparazione || urls.nuovaRiparazione || "";
        }
        if (destinazione === "nuovo_cliente") {
            return urls.nuovo_cliente || urls.nuovoCliente || "";
        }
        return urls[destinazione] || "";
    }

    function matchExtraCommands(text, extras) {
        for (var i = 0; i < extras.length; i += 1) {
            var item = extras[i];
            if (!matchesExactOrIncludes(text, item.phrases)) {
                continue;
            }
            var url = resolveDestination(item.destinazione, item.url);
            if (!url) {
                toast("Destinazione non configurata", true);
                return true;
            }
            toast(item.etichetta || item.phrases[0] || "Comando personalizzato");
            return go(url);
        }
        return false;
    }

    function showHelp(map, extras) {
        var samples = [];
        (extras || []).forEach(function (item) {
            if (item.phrases && item.phrases[0]) {
                samples.push(item.phrases[0]);
            }
        });
        ["riparazioni", "nuova_riparazione", "anagrafiche", "pagina_successiva", "cerca", "aiuto"].forEach(
            function (key) {
                var list = phrases(map, key);
                if (list.length) {
                    samples.push(list[0]);
                }
            }
        );
        toast("Comandi: " + (samples.slice(0, 8).join(", ") || "nessuno configurato") + " …");
    }

    function matchCommand(transcript, map, extras) {
        var text = normalize(transcript);
        if (!text) {
            return false;
        }

        var urls = window.labrepairVoiceUrls || {};

        if (matchExtraCommands(text, extras || [])) {
            return true;
        }

        if (matchesExactOrIncludes(text, phrases(map, "aiuto"))) {
            showHelp(map, extras);
            return true;
        }

        // Destinazioni esplicite: "cerca nelle riparazioni Rossi" / "cerca cliente Bianchi"
        var cercaRip = matchPrefix(text, [
            "cerca nelle riparazioni",
            "cerca riparazioni",
            "cerca riparazione",
            "cerca nelle pratiche",
            "cerca pratiche",
        ]);
        if (cercaRip.matched) {
            if (!cercaRip.rest) {
                toast("Di' ad esempio: cerca nelle riparazioni Rossi", true);
                return true;
            }
            if (search(cercaRip.rest, "riparazioni")) {
                toast("Cerco nelle riparazioni: " + cercaRip.rest);
                return true;
            }
            toast("Ricerca riparazioni non disponibile", true);
            return true;
        }

        var cercaAna = matchPrefix(text, [
            "cerca nelle anagrafiche",
            "cerca anagrafiche",
            "cerca anagrafica",
            "cerca clienti",
            "cerca cliente",
        ]);
        if (cercaAna.matched) {
            if (!cercaAna.rest) {
                toast("Di' ad esempio: cerca cliente Rossi", true);
                return true;
            }
            if (search(cercaAna.rest, "anagrafiche")) {
                toast("Cerco nelle anagrafiche: " + cercaAna.rest);
                return true;
            }
            toast("Ricerca anagrafiche non disponibile", true);
            return true;
        }

        var cerca = matchPrefix(text, phrases(map, "cerca"));
        if (cerca.matched) {
            if (!cerca.rest) {
                toast("Di' ad esempio: cerca Rossi", true);
                return true;
            }
            // Sulla lista corrente usa quel form; altrimenti apre Riparazioni con q=
            if (search(cerca.rest)) {
                toast("Cerco: " + cerca.rest);
                return true;
            }
            toast("Nessun campo ricerca disponibile", true);
            return true;
        }

        if (matchesExactOrIncludes(text, phrases(map, "pagina_successiva"))) {
            if (clickIfPresent("[data-page-next]")) {
                toast("Pagina successiva");
                return true;
            }
            toast("Non c'è una pagina successiva", true);
            return true;
        }

        if (matchesExactOrIncludes(text, phrases(map, "pagina_precedente"))) {
            if (clickIfPresent("[data-page-prev]")) {
                toast("Pagina precedente");
                return true;
            }
            toast("Non c'è una pagina precedente", true);
            return true;
        }

        if (matchesExactOrIncludes(text, phrases(map, "prima_pagina"))) {
            var first = document.querySelector(".st-pagination a[aria-label='Prima pagina']");
            if (first) {
                window.location.href = first.getAttribute("href");
                toast("Prima pagina");
                return true;
            }
            toast("Paginazione non disponibile", true);
            return true;
        }

        if (matchesExactOrIncludes(text, phrases(map, "ultima_pagina"))) {
            if (clickIfPresent("[data-page-last]")) {
                toast("Ultima pagina");
                return true;
            }
            toast("Paginazione non disponibile", true);
            return true;
        }

        var vai = matchPrefix(text, phrases(map, "vai_pagina"));
        if (vai.matched && /^\d+$/.test(vai.rest)) {
            var jump = document.querySelector("[data-page-jump]");
            if (jump) {
                var pageInput = jump.querySelector("input[name='page']");
                if (pageInput) {
                    pageInput.value = vai.rest;
                    jump.submit();
                    toast("Pagina " + vai.rest);
                    return true;
                }
            }
            toast("Paginazione non disponibile", true);
            return true;
        }

        var nav = [
            { key: "nuova_riparazione", url: urls.nuova_riparazione || urls.nuovaRiparazione, label: "Nuova riparazione" },
            { key: "nuovo_cliente", url: urls.nuovo_cliente || urls.nuovoCliente, label: "Nuovo cliente" },
            { key: "riparazioni", url: urls.riparazioni, label: "Riparazioni" },
            { key: "anagrafiche", url: urls.anagrafiche, label: "Anagrafiche" },
            { key: "agenda", url: urls.agenda, label: "Agenda" },
            { key: "dashboard", url: urls.dashboard, label: "Dashboard" },
            { key: "parametri", url: urls.parametri, label: "Parametri" },
            { key: "comandi_vocali", url: urls.comandi_vocali, label: "Comandi vocali" },
        ];

        for (var i = 0; i < nav.length; i += 1) {
            if (matchesExactOrIncludes(text, phrases(map, nav[i].key))) {
                toast(nav[i].label);
                return go(nav[i].url);
            }
        }

        toast('Comando non riconosciuto: "' + transcript + '"', true);
        return false;
    }

    ready(function () {
        var body = document.body;
        if (!body || body.getAttribute("data-voice-commands") !== "1") {
            return;
        }

        var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        var btn = document.getElementById("stVoiceCommandBtn");
        if (!btn) {
            return;
        }
        if (!SpeechRecognition) {
            btn.title = "Comandi vocali non supportati da questo browser";
            btn.disabled = true;
            return;
        }

        var commandMap = loadCommandMap();
        var extraCommands = loadExtraCommands();
        var recognition = new SpeechRecognition();
        recognition.lang = body.getAttribute("data-voice-lang") || "it-IT";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.continuous = false;

        var listening = false;

        function setListening(on) {
            listening = on;
            btn.classList.toggle("is-listening", on);
            btn.setAttribute("aria-pressed", on ? "true" : "false");
            btn.title = on ? "In ascolto… clic per fermare" : "Comandi vocali";
        }

        recognition.onstart = function () {
            setListening(true);
            toast("Ti ascolto…");
        };
        recognition.onend = function () {
            setListening(false);
        };
        recognition.onerror = function (event) {
            setListening(false);
            if (event.error === "not-allowed") {
                toast("Permesso microfono negato", true);
            } else if (event.error !== "aborted" && event.error !== "no-speech") {
                toast("Errore riconoscimento: " + event.error, true);
            }
        };
        recognition.onresult = function (event) {
            var transcript = "";
            if (event.results && event.results[0] && event.results[0][0]) {
                transcript = event.results[0][0].transcript || "";
            }
            if (transcript) {
                matchCommand(transcript, commandMap, extraCommands);
            }
        };

        btn.addEventListener("click", function () {
            if (listening) {
                try {
                    recognition.stop();
                } catch (err) {
                    /* ignore */
                }
                return;
            }
            try {
                recognition.start();
            } catch (err) {
                toast("Impossibile avviare il microfono", true);
            }
        });
    });
})();
