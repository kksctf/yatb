"""
htmx-facing twins of the pure JSON endpoints.

These exist so that `api/` stays free of presentation concerns: the JSON API answers with
status codes and models, this module answers with toasts and out-of-band swaps. Both are
thin mappers over the same service call, so the two can never drift apart.
"""

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from starlette.responses import Response

from yatb import auth
from yatb.api.settings import ExtraInfoForm, api_settings_profile_set
from yatb.db import TaskDB, UserDB
from yatb.i18n import ntranslate as ngettext
from yatb.i18n import translate as _
from yatb.schema import FlagForm, UserID
from yatb.services.flags import FlagOutcome, FlagResult, submit_flag
from yatb.toasts import FLAG_ACCEPTED_EVENT, Toast, ToastKind, toast_header

from .util import response_generator

router = APIRouter(
    prefix="/ui",
    tags=["ui"],
    include_in_schema=False,
)


def flag_toast(result: FlagResult) -> Toast:
    """
    Describe a flag submission to the user.

    A function rather than a module-level table on purpose: `_()` resolves the language
    from a ContextVar set per request, so a dict built at import time would be frozen in
    the default locale forever.
    """
    match result.outcome:
        case FlagOutcome.OK:
            points = result.task.scoring.points if result.task else 0
            return Toast(
                kind=ToastKind.SUCCESS,
                title=_("Flag accepted!"),
                message=ngettext("+%(points)d point", "+%(points)d points", points) % {"points": points},
            )

        case FlagOutcome.ALREADY_SOLVED:
            return Toast(
                kind=ToastKind.INFO,
                message=_("You have already solved this task."),
            )

        case FlagOutcome.BAD_FLAG:
            return Toast(
                kind=ToastKind.DANGER,
                message=_("Wrong flag."),
            )

        case FlagOutcome.NOT_STARTED:
            return Toast(
                kind=ToastKind.WARNING,
                message=_("The CTF has not started yet."),
            )

        case FlagOutcome.DESYNC:
            return Toast(
                kind=ToastKind.DANGER,
                # The Russian catalog keeps the original пятисотОЧКА joke as the msgstr;
                # the msgid stays plain so non-Russian players get a plain message.
                message=_("Something went wrong on our side. Please submit the flag again."),
            )


async def _card_names(task: TaskDB) -> dict[UserID, str]:
    """
    Just the one or two names the card footer shows.

    Deliberately not `view.get_cache()`: that scans every user and every task, and flag
    submission is the hottest endpoint of a running CTF.
    """
    wanted = {pwn[0] for pwn in (task.first_pwned_str(), task.last_pwned_str()) if pwn}
    names: dict[UserID, str] = {}
    for user_id in wanted:
        if found := await UserDB.find_by_user_uuid(user_id):
            names[user_id] = found.display_name
    return names


@router.post("/tasks/submit_flag")
async def ui_task_submit_flag(
    req: Request,
    flag: Annotated[FlagForm, Form()],
    user: auth.CURR_USER,
) -> Response:
    result = await submit_flag(user, flag.flag)
    accepted = result.outcome in (FlagOutcome.OK, FlagOutcome.ALREADY_SOLVED)
    # Only an accepted flag empties the box: a wrong one stays put so it can be edited.
    headers = toast_header(flag_toast(result), {FLAG_ACCEPTED_EVENT: True} if accepted else None)

    if not accepted or result.task is None:
        # Nothing to redraw — the toast is the whole response.
        return HTMLResponse("", headers=headers)

    # Re-rendering the real card beats patching classes from JS: the markup can only ever
    # agree with the server, and ALREADY_SOLVED repairs a card that had gone stale.
    return await response_generator(
        req,
        "partials/task_card.jhtml",
        {
            "curr_user": user,
            "task": result.task,
            "uid2name": await _card_names(result.task),
            "oob": True,
        },
        headers=headers,
    )


@router.post("/settings/profile")
async def ui_settings_profile_set(
    user: auth.CURR_USER,
    form: Annotated[ExtraInfoForm, Form()],
) -> Response:
    await api_settings_profile_set(user=user, form=form)
    return HTMLResponse(
        "",
        headers=toast_header(Toast(kind=ToastKind.SUCCESS, message=_("Profile saved."))),
    )
