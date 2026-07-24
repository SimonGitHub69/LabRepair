(function () {
    function fileKey(file) {
        return [file.name, file.size, file.lastModified].join(":");
    }

    function createPendingItem(file, key) {
        const item = document.createElement("div");
        item.className = "st-pratica-foto-item";
        item.dataset.pendingFoto = key;

        const link = document.createElement("a");
        link.className = "st-pratica-foto-link";
        link.href = URL.createObjectURL(file);
        link.target = "_blank";
        link.rel = "noopener";

        const image = document.createElement("img");
        image.className = "st-pratica-foto-thumb";
        image.alt = file.name;
        image.src = link.href;

        link.appendChild(image);

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "btn btn-icon btn-sm btn-outline-danger st-pratica-foto-remove";
        removeButton.dataset.removePending = key;
        removeButton.title = "Rimuovi foto";
        removeButton.innerHTML = '<i class="ti ti-trash"></i>';

        item.appendChild(link);
        item.appendChild(removeButton);
        return item;
    }

    function initPraticaFoto(root) {
        const input = root.querySelector("[data-pratica-foto-input]");
        const gallery = root.querySelector("[data-pratica-foto-gallery]");
        const deletedContainer = root.querySelector("[data-pratica-foto-deleted]");
        const pickButton = root.querySelector("[data-pratica-foto-pick]");

        if (!input || !gallery || !deletedContainer) {
            return null;
        }

        const pendingFiles = new Map();
        const deletedIds = new Set();

        function hideEmptyState() {
            const emptyState = gallery.querySelector("[data-pratica-foto-empty]");
            if (emptyState) {
                emptyState.remove();
            }
            gallery.classList.remove("is-empty");
        }

        function syncInputFiles() {
            const transfer = new DataTransfer();
            pendingFiles.forEach(function (file) {
                transfer.items.add(file);
            });
            input.files = transfer.files;
        }

        function renderDeletedInputs() {
            deletedContainer.innerHTML = "";
            deletedIds.forEach(function (id) {
                const hidden = document.createElement("input");
                hidden.type = "hidden";
                hidden.name = "foto_elimina";
                hidden.value = id;
                deletedContainer.appendChild(hidden);
            });
        }

        function renderPendingItems() {
            gallery.querySelectorAll("[data-pending-foto]").forEach(function (item) {
                item.remove();
            });

            pendingFiles.forEach(function (file, key) {
                gallery.appendChild(createPendingItem(file, key));
            });

            if (pendingFiles.size > 0 || gallery.querySelector("[data-existing-foto]:not(.is-deleted)")) {
                hideEmptyState();
            }
        }

        function markExistingDeleted() {
            gallery.querySelectorAll("[data-existing-foto]").forEach(function (item) {
                item.classList.remove("is-deleted");
            });

            deletedIds.forEach(function (id) {
                const item = gallery.querySelector('[data-existing-foto="' + id + '"]');
                if (item) {
                    item.classList.add("is-deleted");
                }
            });
        }

        function addFiles(files) {
            Array.from(files || []).forEach(function (file) {
                if (!file.type || !file.type.startsWith("image/")) {
                    return;
                }
                pendingFiles.set(fileKey(file), file);
            });
            syncInputFiles();
            renderPendingItems();
            markExistingDeleted();
        }

        function removePending(key) {
            pendingFiles.delete(key);
            syncInputFiles();
            renderPendingItems();
        }

        function removeExisting(id) {
            deletedIds.add(String(id));
            renderDeletedInputs();
            markExistingDeleted();
        }

        if (pickButton) {
            pickButton.addEventListener("click", function () {
                input.click();
            });
        }

        input.addEventListener("change", function () {
            addFiles(input.files);
            input.value = "";
            syncInputFiles();
        });

        gallery.addEventListener("click", function (event) {
            const pendingButton = event.target.closest("[data-remove-pending]");
            if (pendingButton) {
                removePending(pendingButton.dataset.removePending);
                return;
            }

            const existingButton = event.target.closest("[data-remove-existing]");
            if (existingButton) {
                removeExisting(existingButton.dataset.removeExisting);
            }
        });

        const controller = {
            addFiles: addFiles,
            getInput: function () {
                return input;
            },
        };

        root._praticaFotoController = controller;
        return controller;
    }

    document.addEventListener("DOMContentLoaded", function () {
        const controllers = [];
        document.querySelectorAll("[data-pratica-foto-root]").forEach(function (root) {
            const controller = initPraticaFoto(root);
            if (controller) {
                controllers.push(controller);
            }
        });

        window.LabRepairPraticaFoto = {
            addFiles: function (files) {
                if (!controllers.length) {
                    return;
                }
                controllers[0].addFiles(files);
            },
            getInput: function () {
                if (!controllers.length) {
                    return null;
                }
                return controllers[0].getInput();
            },
        };
    });
})();
