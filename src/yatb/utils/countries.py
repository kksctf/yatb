import functools

from babel import Locale

from yatb import i18n

# babel's territory list is CLDR, not ISO 3166-1: it also carries macro-regions and
# specials that are not places a user can be from. Everything else in the two-letter
# alpha set is a real (if sometimes exceptionally-reserved) territory.
_NOT_COUNTRIES = frozenset({"EU", "EZ", "UN", "QO", "XA", "XB", "ZZ"})

_ALPHA2_LEN = 2

VALID_COUNTRIES: frozenset[str] = (
    frozenset(
        code
        for code in Locale.parse(i18n.DEFAULT).territories
        if isinstance(code, str) and len(code) == _ALPHA2_LEN and code.isalpha()
    )
    - _NOT_COUNTRIES
)


@functools.lru_cache(maxsize=len(i18n.SUPPORTED))
def _names(lang: str) -> dict[str, str]:
    territories = Locale.parse(lang).territories
    return {code: territories[code] for code in VALID_COUNTRIES if code in territories}


def country_list(lang: str) -> list[tuple[str, str]]:
    """(code, localized name) pairs, sorted by name in the given language."""
    return sorted(_names(lang).items(), key=lambda pair: pair[1])


def country_name(code: str, lang: str) -> str:
    """Localized name for an ISO code, or the code itself if CLDR does not know it."""
    return _names(lang).get(code, code)
