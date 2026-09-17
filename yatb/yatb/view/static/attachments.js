(function () {
    "use strict";

    const script = document.currentScript;
    const copiedMessage = script.dataset.copiedMessage;
    const errorMessage = script.dataset.copyErrorMessage;

    function fallbackCopy(text) {
        const focused = document.activeElement;
        const field = document.createElement("textarea");
        field.value = text;
        field.readOnly = true;
        field.style.position = "fixed";
        field.style.left = "-9999px";
        document.body.appendChild(field);
        try {
            field.select();
            if (!document.execCommand("copy")) throw new Error("Copy failed");
        } finally {
            field.remove();
            if (focused instanceof HTMLElement) focused.focus({ preventScroll: true });
        }
    }

    async function copy(text) {
        if (window.isSecureContext && navigator.clipboard) {
            try {
                await navigator.clipboard.writeText(text);
                return;
            } catch (_) {
                // Permission denial can still allow copying from a selected field.
            }
        }
        fallbackCopy(text);
    }

    document.addEventListener("click", async function (event) {
        const button = event.target.closest("button.task-copy[data-copy-text]");
        if (!button || button.getAttribute("aria-disabled") === "true") return;
        const feedback = button.closest(".task-attachment").querySelector(".task-copy-feedback");
        button.setAttribute("aria-disabled", "true");
        try {
            await copy(button.dataset.copyText);
            button.classList.add("is-success");
            feedback.textContent = copiedMessage;
        } catch (_) {
            window.YATB.toast({ kind: "danger", message: errorMessage });
        } finally {
            setTimeout(function () {
                button.removeAttribute("aria-disabled");
                button.classList.remove("is-success");
                feedback.textContent = "";
            }, 1000);
        }
    });
})();
