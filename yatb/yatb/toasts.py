"""
Server-authored toast notifications, delivered to htmx via the `HX-Trigger` header.

The client is deliberately dumb: it never maps status codes to colours, it just renders
what it is told. That mapping belongs next to the code that knows what happened, which is
also the only place where the right translation is knowable.

Lives at package root rather than under `view/` so that `api/` handlers can attach a toast
to an `HTTPException` without importing the view package (which imports `api` back).
"""

import json
from enum import StrEnum

from pydantic import BaseModel

# htmx dispatches these as CustomEvents on the triggering element, and they bubble.
# static/toasts.js listens for TOAST_EVENT on document.body; FLAG_ACCEPTED_EVENT is
# consumed by an `hx-on:` attribute on the flag form itself.
TOAST_EVENT = "yatb:toast"
FLAG_ACCEPTED_EVENT = "yatb:flag-accepted"


class ToastKind(StrEnum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


class ToastLink(BaseModel):
    href: str
    label: str


class Toast(BaseModel):
    kind: ToastKind
    message: str
    title: str | None = None
    link: ToastLink | None = None


def toast_header(toast: Toast, extra: dict[str, object] | None = None) -> dict[str, str]:
    """
    Render a toast as an `HX-Trigger` header value.

    Safe to attach to `HTTPException(headers=...)` as well as to a plain response: htmx
    processes `HX-Trigger` in `handleAjaxResponse` before it decides whether the response
    counts as an error, so 4xx/5xx carry toasts just as well as 200s.

    `extra` piggybacks further events onto the same header, which is how callers signal
    things a toast should not be responsible for (clearing an input, say) to plain
    `hx-on:` attributes rather than to bespoke JS.
    """
    events: dict[str, object] = {TOAST_EVENT: toast.model_dump(exclude_none=True)}
    if extra:
        events.update(extra)
    return {"HX-Trigger": json.dumps(events)}


def danger(message: str) -> dict[str, str]:
    """Shorthand for the common `raise HTTPException(..., headers=...)` case."""
    return toast_header(Toast(kind=ToastKind.DANGER, message=message))


def warning(message: str) -> dict[str, str]:
    return toast_header(Toast(kind=ToastKind.WARNING, message=message))
