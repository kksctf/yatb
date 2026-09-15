/*
 * Toast notifications.
 *
 * The server decides what a toast says and what colour it is, and ships that decision in
 * an `HX-Trigger: {"yatb:toast": {...}}` header. This file only renders. Keeping the
 * classification server-side is deliberate: it lives next to the code that knows what
 * happened, and it is the only place where the right translation is knowable.
 *
 * Public API, for the handful of cases that have no request behind them:
 *   YATB.toast({ kind: "info", message: "...", title: "...", link: {href, label} })
 */
(function () {
    "use strict";

    var TOAST_EVENT = "yatb:toast";
    var DURATION_MS = 4500;
    var LEAVE_MS = 180;
    // Beyond this the stack stops being a notification and starts being a wall.
    var STACK_LIMIT = 4;

    var KIND_CLASS = {
        success: "is-success",
        info: "is-info",
        warning: "is-warning",
        danger: "is-danger",
    };

    // Strings the client raises on its own — everything else is translated server-side.
    var script = document.currentScript;
    var STRINGS = {
        error: (script && script.dataset.errorMessage) || "Something went wrong.",
        offline: (script && script.dataset.offlineMessage) || "Could not reach the server.",
        close: (script && script.dataset.closeLabel) || "Close",
    };

    var stack = null;

    function ensureStack() {
        if (stack && stack.isConnected) return stack;
        stack = document.createElement("div");
        stack.className = "app-toast-stack";
        stack.setAttribute("aria-live", "polite");
        stack.setAttribute("aria-atomic", "true");
        document.body.appendChild(stack);
        return stack;
    }

    // Server-authored today, but a toast is a fine place for a task name to end up, and
    // task names are admin-editable. Anything but an in-app path is dropped.
    function safeHref(href) {
        return typeof href === "string" && /^\/(?!\/)/.test(href) ? href : null;
    }

    function build(toast) {
        var el = document.createElement("div");
        el.className = "notification app-toast " + (KIND_CLASS[toast.kind] || KIND_CLASS.info);
        // Errors interrupt; the rest can wait for a natural pause in screen-reader output.
        el.setAttribute("role", toast.kind === "danger" ? "alert" : "status");

        var closeButton = document.createElement("button");
        closeButton.className = "delete";
        closeButton.type = "button";
        closeButton.setAttribute("aria-label", STRINGS.close);
        el.appendChild(closeButton);

        var body = document.createElement("div");
        body.className = "app-toast-message";

        if (toast.title) {
            var title = document.createElement("strong");
            title.className = "app-toast-title";
            title.textContent = toast.title;
            body.appendChild(title);
        }

        if (toast.message) {
            var message = document.createElement("span");
            message.textContent = toast.message;
            body.appendChild(message);
        }

        // textContent throughout, never innerHTML: that is what keeps an admin-authored
        // task name from becoming stored XSS for every player.
        if (toast.link && safeHref(toast.link.href)) {
            var link = document.createElement("a");
            link.className = "app-toast-link";
            link.href = safeHref(toast.link.href);
            link.textContent = toast.link.label || toast.link.href;
            body.appendChild(link);
        }

        el.appendChild(body);
        return { el: el, closeButton: closeButton };
    }

    function show(toast) {
        if (!toast || (!toast.message && !toast.title)) return;

        var host = ensureStack();
        var built = build(toast);
        var el = built.el;

        host.appendChild(el);
        while (host.children.length > STACK_LIMIT) {
            host.removeChild(host.firstElementChild);
        }

        var hideTimer = null;
        var endAt = Date.now() + DURATION_MS;

        function close() {
            if (!el.isConnected) return;
            el.classList.remove("is-visible");
            el.classList.add("is-leaving");
            setTimeout(function () {
                if (el.isConnected) el.remove();
            }, LEAVE_MS);
        }

        function scheduleHide(delay) {
            if (hideTimer) clearTimeout(hideTimer);
            hideTimer = setTimeout(close, Math.max(0, delay));
        }

        requestAnimationFrame(function () {
            el.classList.add("is-visible");
        });
        scheduleHide(DURATION_MS);

        el.addEventListener("mouseenter", function () {
            if (hideTimer) clearTimeout(hideTimer);
        });
        el.addEventListener("mouseleave", function () {
            scheduleHide(endAt - Date.now());
        });
        built.closeButton.addEventListener("click", close);

        return close;
    }

    function serverSentToast(xhr) {
        // htmx has already dispatched the event if the header carried one; this only asks
        // whether it did, so the fallback does not double up on an explained failure.
        try {
            var header = xhr && xhr.getResponseHeader("HX-Trigger");
            return !!header && header.indexOf(TOAST_EVENT) !== -1;
        } catch (_) {
            return false;
        }
    }

    document.body.addEventListener(TOAST_EVENT, function (event) {
        show(event.detail);
    });

    // Anything the server did not explain itself: 5xx from middleware, a proxy error page,
    // a response that never made it back at all.
    document.body.addEventListener("htmx:responseError", function (event) {
        if (event.detail && serverSentToast(event.detail.xhr)) return;
        show({ kind: "danger", message: STRINGS.error });
    });

    document.body.addEventListener("htmx:sendError", function () {
        show({ kind: "danger", message: STRINGS.offline });
    });

    window.YATB = window.YATB || {};
    window.YATB.toast = show;
})();
