from yatb.ebasemodelv2 import EBaseModelV2, Public
from yatb.ui_types import LangPref, Theme


class UISettings(EBaseModelV2):
    """Tier-1 preferences: needed before authentication, mirrored into cookies."""

    theme: Public[Theme] = "auto"
    lang: Public[LangPref] = "auto"
