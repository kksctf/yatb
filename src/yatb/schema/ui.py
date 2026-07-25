from typing import Literal

from yatb import i18n
from yatb.ebasemodelv2 import EBaseModelV2, Public

# Kept in sync with i18n.SUPPORTED_THEMES / i18n.SUPPORTED_LANG_PREFS by the asserts below:
# Literal cannot be built from a runtime list, so the constants are spelled out once here
# and checked against the middleware's source of truth at import time.
Theme = Literal["auto", "light", "dark"]
LangPref = Literal["auto", "en", "ru"]

assert set(i18n.SUPPORTED_THEMES) == set(Theme.__args__)  # noqa: S101
assert set(i18n.SUPPORTED_LANG_PREFS) == set(LangPref.__args__)  # noqa: S101


class UISettings(EBaseModelV2):
    """Tier-1 preferences: needed before authentication, mirrored into cookies."""

    theme: Public[Theme] = "auto"
    lang: Public[LangPref] = "auto"
