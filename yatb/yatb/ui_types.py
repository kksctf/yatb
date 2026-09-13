from typing import Literal

Language = Literal["en", "ru"]
LangPref = Language | Literal["auto"]
Theme = Literal["auto", "light", "dark"]
