from typing import Annotated, Union, TypeAlias

from pydantic import Field

from ...config import settings
from ...utils.log_helper import get_logger
from .auth_base import AuthBase
from .oauth import CTFTimeOAuth, DiscordOAuth, GithubOAuth, OAuth
from .simple import SimpleAuth
from .tg import TelegramAuth

logger = get_logger("schema.auth")

ENABLED_AUTH_WAYS: list[type[AuthBase]] = []

for auth_way in settings.ENABLED_AUTH_WAYS:
    try:
        ENABLED_AUTH_WAYS.append(globals()[auth_way])
    except KeyError as ex:
        logger.critical(f"{auth_way} not found")
        raise Exception("death") from ex  # noqa: TRY002, EM101

logger.info(f"Loaded next auth ways: {ENABLED_AUTH_WAYS}")

RAW_AUTH_MODELS = tuple([x.AuthModel for x in ENABLED_AUTH_WAYS])
# TYPING_AUTH = (
#     CTFTimeOAuth.AuthModel | SimpleAuth.AuthModel | TelegramAuth.AuthModel | GithubOAuth.AuthModel
# )
TYPING_AUTH = Union[RAW_AUTH_MODELS]  # type: ignore # noqa: UP007

ANNOTATED_TYPING_AUTH = Annotated[
    TYPING_AUTH,
    Field(discriminator="classtype"),
]
