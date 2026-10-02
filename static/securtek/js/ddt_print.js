/**
 * Stampa DDT senza lasciare la pagina: scarica il PDF e apre il dialogo di stampa.
 * Su Annulla ripristina subito l'UI (niente attese lunghe).
 */
(function () {
    var busy = false;

    function ensureFormatPdf(url) {
        try {
            var parsed = new URL(url, window.location.origin);
            parsed.searchParams.set("format", "pdf");
            return parsed.toString();
        } catch (e) {
            if (url.indexOf("format=pdf") !== -1) return url;
            return url + (url.indexOf("?") >= 0 ? "&" : "?") + "format=pdf";
        }
    }

    function printPdfBlob(blob) {
        return new Promise(function (resolve, reject) {
            var objectUrl = URL.createObjectURL(blob);
            var frame = document.createElement("iframe");
            frame.setAttribute("aria-hidden", "true");
            frame.style.cssText =
                "position:absolute;width:1px;height:1px;left:-9999px;top:0;opacity:0;border:0;pointer-events:none;";
            var cleaned = false;
            var resolved = false;

            function cleanup() {
                if (cleaned) return;
                cleaned = true;
                try {
                    URL.revokeObjectURL(objectUrl);
                } catch (e) {}
                if (frame.parentNode) {
                    frame.parentNode.removeChild(frame);
                }
            }

            function finishUi() {
                if (resolved) return;
                resolved = true;
                resolve();
            }

            frame.onload = function () {
                // Tempo minimo solo per far caricare il viewer PDF nell'iframe.
                setTimeout(function () {
                    try {
                        var win = frame.contentWindow;
                        if (!win) {
                            cleanup();
                            finishUi();
                            return;
                        }

                        var onDone = function () {
                            window.removeEventListener("focus", onFocus);
                            cleanup();
                        };
                        var onFocus = function () {
                            // Dialogo chiuso (stampa o annulla): libera subito le risorse.
                            window.removeEventListener("focus", onFocus);
                            cleanup();
                        };

                        win.addEventListener("afterprint", onDone, { once: true });
                        window.addEventListener("focus", onFocus);

                        win.focus();
                        win.print();
                        // Non attendere la chiusura del dialogo: sblocca subito il pulsante.
                        finishUi();
                        // Safety net se afterprint/focus non arrivano.
                        setTimeout(cleanup, 60000);
                    } catch (err) {
                        cleanup();
                        reject(err);
                    }
                }, 80);
            };

            frame.onerror = function () {
                cleanup();
                reject(new Error("Impossibile caricare il PDF per la stampa."));
            };

            document.body.appendChild(frame);
            frame.src = objectUrl;
        });
    }

    async function printFromLink(anchor) {
        if (busy) return;
        busy = true;
        anchor.classList.add("disabled");
        var originalHtml = anchor.innerHTML;
        try {
            anchor.innerHTML = '<i class="ti ti-loader-2"></i> Stampa…';
            var response = await fetch(ensureFormatPdf(anchor.href), {
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: "same-origin",
            });
            if (!response.ok) {
                throw new Error("Errore nel preparare il DDT (" + response.status + ").");
            }
            var blob = await response.blob();
            if (!blob || !blob.size) {
                throw new Error("PDF vuoto.");
            }
            await printPdfBlob(blob);
        } catch (err) {
            window.alert(err && err.message ? err.message : "Stampa DDT non riuscita.");
        } finally {
            anchor.innerHTML = originalHtml;
            anchor.classList.remove("disabled");
            busy = false;
        }
    }

    document.addEventListener("click", function (event) {
        var anchor = event.target.closest("a.js-ddt-print");
        if (!anchor) return;
        if (event.button !== 0) return;
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        printFromLink(anchor);
    });
})();
