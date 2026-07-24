(function () {
    function getWebcamHotkeys() {
        return {
            scatto: (document.body.dataset.webcamHotkeyScatto || "").trim(),
            usa: (document.body.dataset.webcamHotkeyUsa || "").trim(),
            nuovoScatto: (document.body.dataset.webcamHotkeyNuovoScatto || "").trim(),
        };
    }

    function isTypingTarget(element) {
        if (!element) {
            return false;
        }
        const tag = element.tagName;
        return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || element.isContentEditable;
    }

    function getPrimaryWebcamTrigger() {
        return document.querySelector("[data-webcam-trigger]");
    }

    function openPrimaryWebcamTrigger() {
        const trigger = getPrimaryWebcamTrigger();
        if (trigger) {
            trigger.click();
            return true;
        }
        return false;
    }

    function supportsWebcam() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    function isSecureWebcamContext() {
        if (window.isSecureContext) {
            return true;
        }
        const host = (window.location.hostname || "").toLowerCase();
        return host === "localhost" || host === "127.0.0.1" || host === "[::1]";
    }

    function webcamUnsupportedMessage() {
        const origin = window.location.origin || "";
        if (!isSecureWebcamContext()) {
            return (
                "Webcam bloccata su HTTP in rete. " +
                "Ora sei su " + origin + ". " +
                "Soluzione rapida: sul PC della webcam usa lo script " +
                "scripts\\\\enable_chrome_webcam_lan.ps1 " +
                "oppure apri LabRepair in HTTPS / da http://127.0.0.1."
            );
        }
        return "Il browser non supporta l'accesso alla webcam.";
    }

    function timestampFilename(prefix) {
        const now = new Date();
        const pad = (value) => String(value).padStart(2, "0");
        return `${prefix}-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}.jpg`;
    }

    function preferPreferredWebcam(devices) {
        const videoInputs = devices.filter((device) => device.kind === "videoinput");
        if (!videoInputs.length) {
            return null;
        }

        // Preferisci webcam USB di banco (Mediacom, Nilox, Logitech, …) rispetto alla camera del notebook.
        const preferred = videoInputs.find((device) =>
            /mediacom|nilox|logitech|910|c910|hd pro webcam|doc.?cam|document.?cam/i.test(device.label || "")
        );
        if (preferred) {
            return preferred;
        }

        const external = videoInputs.find((device) =>
            !/integrated|built.?in|internal|facetime|laptop|notebook/i.test(device.label || "")
        );
        return external || videoInputs[0];
    }

    function WebcamCapture(modal) {
        this.modal = modal;
        this.video = modal.querySelector("[data-webcam-preview]");
        this.capturePreview = modal.querySelector("[data-webcam-capture-preview]");
        this.deviceSelect = modal.querySelector("[data-webcam-device-select]");
        this.statusElement = modal.querySelector("[data-webcam-status]");
        this.captureButton = modal.querySelector("[data-webcam-capture]");
        this.useButton = modal.querySelector("[data-webcam-use]");
        this.retakeButton = modal.querySelector("[data-webcam-retake]");
        this.downloadButton = modal.querySelector("[data-webcam-download]");
        this.closeButtons = modal.querySelectorAll("[data-webcam-close]");
        this.stream = null;
        this.capturedBlob = null;
        this.fileInput = null;
        this.previewImage = null;
        this.mode = "attach";
        this.onUse = null;
        this.keepOpen = false;
    }

    WebcamCapture.prototype.setStatus = function (message, isError) {
        if (!this.statusElement) {
            return;
        }
        this.statusElement.textContent = message;
        this.statusElement.classList.toggle("text-danger", !!isError);
    };

    WebcamCapture.prototype.stopStream = function () {
        if (this.stream) {
            this.stream.getTracks().forEach(function (track) {
                track.stop();
            });
            this.stream = null;
        }
        if (this.video) {
            this.video.srcObject = null;
        }
    };

    WebcamCapture.prototype.resetCapture = function () {
        this.capturedBlob = null;
        if (this.capturePreview) {
            this.capturePreview.hidden = true;
            this.capturePreview.removeAttribute("src");
        }
        if (this.video) {
            this.video.hidden = false;
        }
        if (this.captureButton) {
            this.captureButton.hidden = false;
        }
        if (this.useButton) {
            this.useButton.hidden = true;
        }
        if (this.retakeButton) {
            this.retakeButton.hidden = true;
        }
        if (this.downloadButton) {
            this.downloadButton.hidden = true;
        }
    };

    WebcamCapture.prototype.populateDevices = function (devices) {
        const videoInputs = devices.filter((device) => device.kind === "videoinput");
        this.deviceSelect.innerHTML = "";

        if (!videoInputs.length) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Nessuna videocamera rilevata";
            this.deviceSelect.appendChild(option);
            this.deviceSelect.disabled = true;
            return;
        }

        videoInputs.forEach(function (device) {
            const option = document.createElement("option");
            option.value = device.deviceId;
            option.textContent = device.label || `Videocamera ${device.deviceId.slice(0, 6)}`;
            this.deviceSelect.appendChild(option);
        }, this);

        this.deviceSelect.disabled = false;
        const preferred = preferPreferredWebcam(devices);
        if (preferred) {
            this.deviceSelect.value = preferred.deviceId;
        }
    };

    WebcamCapture.prototype.buildVideoConstraints = function (deviceId, resolution) {
        const video = {
            width: { ideal: resolution.width },
            height: { ideal: resolution.height },
        };
        if (deviceId) {
            video.deviceId = { exact: deviceId };
        }
        return { video: video, audio: false };
    };

    WebcamCapture.prototype.startStream = async function () {
        if (!supportsWebcam()) {
            this.setStatus(webcamUnsupportedMessage(), true);
            return;
        }

        this.stopStream();
        this.resetCapture();

        const selectedDeviceId = this.deviceSelect.value;
        // Alcune Nilox/USB low-cost non accettano 1080p: prova risoluzioni progressive.
        const resolutions = [
            { width: 1920, height: 1080 },
            { width: 1280, height: 720 },
            { width: 640, height: 480 },
        ];

        let lastError = null;
        for (let i = 0; i < resolutions.length; i++) {
            try {
                this.stream = await navigator.mediaDevices.getUserMedia(
                    this.buildVideoConstraints(selectedDeviceId, resolutions[i])
                );
                this.video.srcObject = this.stream;
                const track = this.stream.getVideoTracks()[0];
                const label = track.label || "Videocamera attiva";
                this.setStatus(label + " pronta.", false);
                await this.ensurePreferredDevice(selectedDeviceId);
                return;
            } catch (error) {
                lastError = error;
                this.stopStream();
            }
        }

        // Ultimo tentativo senza vincolo di device (permessi / default Windows).
        if (selectedDeviceId) {
            try {
                this.stream = await navigator.mediaDevices.getUserMedia(
                    this.buildVideoConstraints("", { width: 1280, height: 720 })
                );
                this.video.srcObject = this.stream;
                const track = this.stream.getVideoTracks()[0];
                const label = track.label || "Videocamera attiva";
                this.setStatus(
                    label + " pronta. Seleziona la Mediacom/USB dal menu se non è quella attiva.",
                    false
                );
                await this.ensurePreferredDevice("");
                return;
            } catch (error) {
                lastError = error;
            }
        }

        const hint =
            lastError && lastError.name === "NotAllowedError"
                ? "Permesso webcam negato dal browser."
                : "Impossibile avviare la webcam. Verifica collegamento USB, driver Mediacom e permessi browser.";
        this.setStatus(hint, true);
    };

    WebcamCapture.prototype.refreshDeviceLabels = async function () {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const current = this.deviceSelect.value;
            this.populateDevices(devices);
            if (current) {
                this.deviceSelect.value = current;
            }
        } catch (error) {
            // ignora
        }
    };

    /**
     * Dopo il primo permesso le label diventano visibili: se c'è una Nilox/Logitech
     * e non era ancora selezionata, passa a quella (una sola volta).
     */
    WebcamCapture.prototype.ensurePreferredDevice = async function (startedWithDeviceId) {
        if (this._preferSwitchDone) {
            return;
        }
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const preferred = preferPreferredWebcam(devices);
            if (!preferred) {
                await this.refreshDeviceLabels();
                return;
            }

            const currentId = this.deviceSelect.value || startedWithDeviceId || "";
            this.populateDevices(devices);

            if (preferred.deviceId === currentId) {
                this.deviceSelect.value = preferred.deviceId;
                return;
            }

            // Solo se non c'era ancora una selezione utile, o se la label preferita è Nilox/Logitech.
            this._preferSwitchDone = true;
            this.deviceSelect.value = preferred.deviceId;
            await this.startStream();
        } catch (error) {
            // ignora
        }
    };

    WebcamCapture.prototype.refreshDevices = async function () {
        if (!supportsWebcam()) {
            this.setStatus(webcamUnsupportedMessage(), true);
            return;
        }

        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            this.populateDevices(devices);
            await this.startStream();
        } catch (error) {
            this.setStatus("Errore durante il rilevamento delle videocamere.", true);
        }
    };

    WebcamCapture.prototype.open = async function (options) {
        this.mode = options.mode || "attach";
        this.fileInput = options.fileInput || null;
        this.previewImage = options.previewImage || null;
        this.onUse = options.onUse || null;
        this.keepOpen = !!options.keepOpen;

        if (this.useButton) {
            this.useButton.hidden = this.mode !== "attach" && this.mode !== "multi";
        }
        if (this.downloadButton) {
            this.downloadButton.hidden = this.mode !== "download";
        }

        this.modal.hidden = false;
        document.body.classList.add("st-webcam-open");

        if (!this.deviceSelect.options.length) {
            await this.refreshDevices();
        } else {
            await this.startStream();
        }
    };

    WebcamCapture.prototype.close = function () {
        this.modal.hidden = true;
        document.body.classList.remove("st-webcam-open");
        this.stopStream();
        this.resetCapture();
        this._preferSwitchDone = false;
    };

    WebcamCapture.prototype.capturePhoto = function () {
        if (!this.video || !this.stream) {
            return;
        }

        const canvas = document.createElement("canvas");
        canvas.width = this.video.videoWidth || 1280;
        canvas.height = this.video.videoHeight || 720;
        const context = canvas.getContext("2d");
        context.drawImage(this.video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob((blob) => {
            if (!blob) {
                this.setStatus("Impossibile acquisire la foto.", true);
                return;
            }

            this.capturedBlob = blob;
            const previewUrl = URL.createObjectURL(blob);
            this.capturePreview.src = previewUrl;
            this.capturePreview.hidden = false;
            this.video.hidden = true;
            this.captureButton.hidden = true;
            this.retakeButton.hidden = false;

            if (this.mode === "attach") {
                this.useButton.hidden = false;
            } else if (this.mode === "multi") {
                this.useButton.hidden = false;
            } else if (this.downloadButton) {
                this.downloadButton.href = previewUrl;
                this.downloadButton.download = timestampFilename("labrepair");
                this.downloadButton.hidden = false;
            }

            this.setStatus("Foto acquisita. Conferma per usarla.", false);
        }, "image/jpeg", 0.92);
    };

    WebcamCapture.prototype.applyCapture = function () {
        if (!this.capturedBlob) {
            return;
        }

        const file = new File([this.capturedBlob], timestampFilename("foto-oggetto"), {
            type: "image/jpeg",
        });

        if (this.mode === "multi") {
            if (window.LabRepairPraticaFoto && typeof window.LabRepairPraticaFoto.addFiles === "function") {
                window.LabRepairPraticaFoto.addFiles([file]);
            } else if (this.fileInput) {
                const transfer = new DataTransfer();
                Array.from(this.fileInput.files || []).forEach(function (existingFile) {
                    transfer.items.add(existingFile);
                });
                transfer.items.add(file);
                this.fileInput.files = transfer.files;
                this.fileInput.dispatchEvent(new Event("change", { bubbles: true }));
            }

            if (typeof this.onUse === "function") {
                this.onUse(file);
            }

            this.resetCapture();
            this.startStream();
            this.setStatus("Foto aggiunta. Puoi scattarne un'altra.", false);

            if (!this.keepOpen) {
                this.close();
            }
            return;
        }

        if (this.fileInput) {
            const transfer = new DataTransfer();
            transfer.items.add(file);
            this.fileInput.files = transfer.files;
            this.fileInput.dispatchEvent(new Event("change", { bubbles: true }));
        }

        if (this.previewImage) {
            this.previewImage.src = URL.createObjectURL(this.capturedBlob);
            this.previewImage.hidden = false;
        }

        if (typeof this.onUse === "function") {
            this.onUse(file);
        }

        this.close();
    };

    WebcamCapture.prototype.isOpen = function () {
        return !!this.modal && !this.modal.hidden;
    };

    WebcamCapture.prototype.canCaptureNow = function () {
        return (
            this.isOpen()
            && !!this.stream
            && !this.capturedBlob
            && this.captureButton
            && !this.captureButton.hidden
        );
    };

    WebcamCapture.prototype.canUsePhotoNow = function () {
        return (
            this.isOpen()
            && !!this.capturedBlob
            && this.useButton
            && !this.useButton.hidden
        );
    };

    WebcamCapture.prototype.canRetakeNow = function () {
        return (
            this.isOpen()
            && this.retakeButton
            && !this.retakeButton.hidden
        );
    };

    WebcamCapture.prototype.handleScattoHotkey = function () {
        if (this.canCaptureNow()) {
            this.capturePhoto();
            return true;
        }

        if (this.isOpen()) {
            return false;
        }

        return openPrimaryWebcamTrigger();
    };

    WebcamCapture.prototype.handleUsePhotoHotkey = function () {
        if (!this.canUsePhotoNow()) {
            return false;
        }

        this.applyCapture();
        return true;
    };

    WebcamCapture.prototype.handleRetakeHotkey = function () {
        if (!this.canRetakeNow()) {
            return false;
        }

        this.resetCapture();
        this.startStream();
        return true;
    };

    WebcamCapture.prototype.bindEvents = function () {
        this.deviceSelect.addEventListener("change", () => {
            this.startStream();
        });

        this.captureButton.addEventListener("click", () => {
            this.capturePhoto();
        });

        this.retakeButton.addEventListener("click", () => {
            this.resetCapture();
            this.startStream();
        });

        this.useButton.addEventListener("click", () => {
            this.applyCapture();
        });

        this.closeButtons.forEach((button) => {
            button.addEventListener("click", () => {
                this.close();
            });
        });

        this.modal.addEventListener("click", (event) => {
            if (event.target === this.modal) {
                this.close();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !this.modal.hidden) {
                this.close();
            }
        });
    };

    function bindGlobalHotkey() {
        document.addEventListener("keydown", function (event) {
            const hotkeys = getWebcamHotkeys();
            const pressedKey = event.key;
            const isScatto = hotkeys.scatto && pressedKey === hotkeys.scatto;
            const isUsa = hotkeys.usa && pressedKey === hotkeys.usa;
            const isNuovoScatto = hotkeys.nuovoScatto && pressedKey === hotkeys.nuovoScatto;

            if (!isScatto && !isUsa && !isNuovoScatto) {
                return;
            }

            const controller = getController();
            const modalOpen = controller && controller.isOpen();

            if (!modalOpen && isTypingTarget(event.target)) {
                return;
            }

            if (isScatto) {
                if (!controller && !getPrimaryWebcamTrigger()) {
                    return;
                }

                event.preventDefault();

                if (controller) {
                    controller.handleScattoHotkey();
                } else {
                    openPrimaryWebcamTrigger();
                }
                return;
            }

            if (!controller || !modalOpen) {
                return;
            }

            event.preventDefault();

            if (isUsa) {
                controller.handleUsePhotoHotkey();
                return;
            }

            if (isNuovoScatto) {
                controller.handleRetakeHotkey();
            }
        });
    }

    let sharedController = null;

    function getController() {
        const modal = document.getElementById("webcamModal");
        if (!modal) {
            return null;
        }
        if (!sharedController) {
            sharedController = new WebcamCapture(modal);
            sharedController.bindEvents();
        }
        return sharedController;
    }

    document.addEventListener("DOMContentLoaded", function () {
        bindGlobalHotkey();

        document.querySelectorAll("[data-webcam-trigger]").forEach(function (button) {
            button.addEventListener("click", function () {
                const controller = getController();
                if (!controller) {
                    return;
                }

                const fileInputId = button.dataset.webcamFileInput;
                const previewId = button.dataset.webcamPreview;
                const fileInput = fileInputId ? document.getElementById(fileInputId) : null;
                const previewImage = previewId ? document.getElementById(previewId) : null;

                controller.open({
                    mode: button.dataset.webcamMode || "attach",
                    fileInput: fileInput,
                    previewImage: previewImage,
                    keepOpen: button.dataset.webcamKeepOpen === "true",
                });
            });
        });
    });

    window.LabRepairWebcam = {
        getController: getController,
        supportsWebcam: supportsWebcam,
    };
})();
