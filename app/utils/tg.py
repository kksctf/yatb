from typing import cast

import requests

from .. import schema
from ..config import settings
from ..utils.log_helper import get_logger

logger = get_logger("api")


def to_tg(data: dict, path: str) -> requests.Response:
    if not settings.BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/{path}"
    ret = requests.post(url, data=data)
    logger.info(f"TG info={ret.text}")
    return ret


def encoder(text: str) -> str:
    bad = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    ret = text
    for b in bad:
        ret = ret.replace(b, f"\\{b}")
    return ret


def send_message(text):
    return to_tg(
        data={
            "chat_id": settings.CHAT_ID,
            "text": text,
            "parse_mode": "MarkdownV2",
        },
        path="sendMessage",
    )


def display_fb_msg(what: schema.Task, by: schema.User):
    if by.auth_source.classtype == "CTFTimeOAuth":
        au = cast(schema.auth.CTFTimeOAuth.AuthModel, by.auth_source)
        message = (
            f"First blood on {encoder(what.task_name)} by "
            f"[{encoder(by.username)}](https://ctftime.org/team/{au.team.id}), yay\\!"
        )
    else:
        message = f"First blood on {encoder(what.task_name)} by {encoder(by.username)}, yay\\!"

    return send_message(message)
