import os
import hashlib
import subprocess
import distutils.util
import datetime


def env_bool(var: str, default: str) -> bool:
    return bool(distutils.util.strtobool(os.environ.get(var, default=default)))


def env_val(var: str, default: str):
    return os.environ.get(var, default=default)


# ==== CLASSES FOR MD RENDERER ====
MD_CLASSES_TASKS = {
    "p": "card-text",
}

MD_ATTRS_TASKS = {
    "a": {
        "target": "_blank",
        "rel": "noopener noreferrer",
        # "class": "btn btn-outline-primary btn-sm col-auto m-1 flex-fill"
    }
}
# ==== CLASSES FOR MD RENDERER ====

# ==== Some options ====
_DEGUG = env_bool("YATB_DEBUG", "True")
TOKEN_PATH = "/api/users/login"  # strange setting, but idk for what i can use it


if ".git" in os.listdir("."):
    VERSION = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode()[:8]
    VERSION += "-Modified" if len(subprocess.check_output(["git", "status", "--porcelain"])) > 0 else ""
else:
    commit = os.environ.get("COMMIT_SHA", None)
    VERSION = "a0.2.11"
    if commit:
        VERSION += f"-{commit[:8]}"
    _DEGUG = False
# ==== Some options ====

# ==== Bot token for notif ====

BOT_TOKEN = env_val("TG_BOT_TOKEN", "")
CHAT_ID = 0
# ==== Bot token for notif ====

# ==== CTFTime OAuth ====
if True:
    OAUTH_ADMIN_IDs = [32621]
    OAUTH_CLIENT_ID = env_val("OAUTH_CLIENT_ID", "")
    OAUTH_CLIENT_SECRET = env_val("OAUTH_CLIENT_SECRET", "")
    OAUTH_ENDPOINT = env_val("OAUTH_ENDPOINT", "https://oauth.ctftime.org/authorize")
    OAUTH_TOKEN_ENDPOINT = env_val("OAUTH_TOKEN_ENDPOINT", "https://oauth.ctftime.org/token")
    OAUTH_API_ENDPOINT = env_val("OAUTH_API_ENDPOINT", "https://oauth.ctftime.org/user")

    EVENT_START_TIME = datetime.datetime(1077, 12, 12, 9, 0)
    EVENT_END_TIME = datetime.datetime(2077, 12, 13, 9, 0)
# ==== CTFTime OAuth ====

# ==== Generic debug/prod settings ====
if _DEGUG:
    DB_NAME = env_val("DB_NAME", os.path.join(".", "file_db") + ".db")

    JWT_SECRET_KEY = "DEBUG_CHANGE_ME"
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # one day

    FASTAPI_DOCS_URL = "/docs"
    FASTAPI_REDOC_URL = "/redoc"
    FASTAPI_OPENAPI_URL = "/openapi.json"

    MONITORING_URL = "/metrics"

    VERSION += "-dev"
else:
    DB_NAME = env_val("DB_NAME", os.path.join(".", "file_db") + ".db")

    JWT_SECRET_KEY = "CHANGE_ME_OR_DIE"
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 2  # two days

    FASTAPI_DOCS_URL = "/kek_docs"
    FASTAPI_REDOC_URL = "/kek_redoc"
    FASTAPI_OPENAPI_URL = "/kek_openapi.json"

    MONITORING_URL = "/kek_metrics"

    VERSION += "-prod"
# ==== Generic debug/prod settings ====

if True:
    VERSION += "-ctf"
