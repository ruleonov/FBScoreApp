"""Translations, set up from day one so Russian can be added later.

All page text goes through `_()` in templates. To add Russian:
    pybabel extract -F babel.cfg -o app/translations/messages.pot .
    pybabel init -i app/translations/messages.pot -d app/translations -l ru
    (translate app/translations/ru/LC_MESSAGES/messages.po)
    pybabel compile -d app/translations
"""
from datetime import date
from functools import lru_cache
from pathlib import Path

from babel.dates import format_date
from babel.support import NullTranslations, Translations

TRANSLATIONS_DIR = Path(__file__).parent / "translations"
SUPPORTED_LOCALES = ["en"]  # add "ru" once its translations exist
DEFAULT_LOCALE = "en"


@lru_cache(maxsize=None)
def get_translations(locale: str):
    if locale == DEFAULT_LOCALE:
        return NullTranslations()
    return Translations.load(str(TRANSLATIONS_DIR), [locale])


def template_context(locale: str = DEFAULT_LOCALE) -> dict:
    """Functions every template can use, bound to one locale."""
    t = get_translations(locale)

    def fmt_date(value: date, fmt: str = "EEE, d MMM") -> str:
        return format_date(value, fmt, locale=locale)

    return {
        "locale": locale,
        "_": t.gettext,
        "gettext": t.gettext,
        "ngettext": t.ngettext,
        "fmt_date": fmt_date,
    }
