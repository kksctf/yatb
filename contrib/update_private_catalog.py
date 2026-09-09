# ruff: noqa: INP001
from pathlib import Path

from babel.messages.catalog import Catalog
from babel.messages.pofile import read_po, write_po


def private_template(extracted: Catalog, public: Catalog, private: Catalog) -> Catalog:
    result = Catalog()
    result.creation_date = extracted.creation_date
    for message in extracted:
        if message.id and (
            public.get(message.id, message.context) is None or private.get(message.id, message.context) is not None
        ):
            result[message.id] = message.clone()
    return result


def update_private_catalogs(template_path: Path, locale_dir: Path) -> None:
    with template_path.open("rb") as source:
        extracted = read_po(source, abort_invalid=True)
    public_paths = sorted(locale_dir.glob("*/LC_MESSAGES/messages.po"))
    if not public_paths:
        raise FileNotFoundError(f"No public catalogs in {locale_dir}")
    for public_path in public_paths:
        locale = public_path.parent.parent.name
        with public_path.open("rb") as source:
            public = read_po(source, locale=locale, abort_invalid=True)
        private_path = public_path.with_name("private.po")
        if private_path.exists():
            with private_path.open("rb") as source:
                private = read_po(source, locale=locale, domain="private", abort_invalid=True)
        else:
            private = Catalog(locale=locale, domain="private", fuzzy=False)
        template = private_template(extracted, public, private)
        if not private_path.exists() and not len(template):
            continue
        private.update(template, no_fuzzy_matching=True)
        with private_path.open("wb") as destination:
            write_po(destination, private, sort_output=True, include_lineno=False)


if __name__ == "__main__":
    update_private_catalogs(Path("private.pot"), Path("src/yatb/locale"))
