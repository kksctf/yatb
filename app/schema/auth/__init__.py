from .auth_base import AuthBase
from .oauth import CTFTimeOAuth, DiscordOAuth, GithubOAuth, OAuth
from .simple import SimpleAuth
from .tg import TelegramAuth

TYPING_AUTH = (
    CTFTimeOAuth.AuthModel
    | SimpleAuth.AuthModel
    | TelegramAuth.AuthModel
    | GithubOAuth.AuthModel
    | OAuth.AuthModel
    | AuthBase.AuthModel
)

ENABLED_AUTH_WAYS = [
    CTFTimeOAuth,
    SimpleAuth,
    TelegramAuth,
    GithubOAuth,
    DiscordOAuth,
]
