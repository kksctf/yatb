from pydantic import BaseModel

from yatb.yatb.ui_types import LangPref, Theme


class UISettings(BaseModel):
    """Tier-1 preferences: needed before authentication, mirrored into cookies."""

    # theme: Public[Theme] = "auto"
    # lang: Public[LangPref] = "auto"
    theme: Theme = "auto"
    lang: LangPref = "auto"
