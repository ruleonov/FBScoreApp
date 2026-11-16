"""Translations. The interface is shown in Russian; team names stay in English.

Text in code and templates is written in English and wrapped in `_()`.
After changing any wrapped text, refresh the Russian file:
    .venv/bin/pybabel extract -F babel.cfg -k N_ -o app/translations/messages.pot .
    .venv/bin/pybabel update -i app/translations/messages.pot -d app/translations
    (translate new entries in app/translations/ru/LC_MESSAGES/messages.po)
    .venv/bin/pybabel compile -d app/translations
"""
from datetime import date
from functools import lru_cache
from pathlib import Path

from babel.dates import format_date
from babel.support import NullTranslations, Translations

TRANSLATIONS_DIR = Path(__file__).parent / "translations"
SUPPORTED_LOCALES = ["ru", "en"]
DEFAULT_LOCALE = "ru"


def N_(text: str) -> str:
    """Mark text for translation without translating it yet (used for data labels)."""
    return text


# Labels that come from the data source rather than templates.
DATA_LABELS = [
    N_("AL East"),
    N_("AL Central"),
    N_("AL West"),
    N_("NL East"),
    N_("NL Central"),
    N_("NL West"),
    N_("AL Wild Card Series"),
    N_("NL Wild Card Series"),
    N_("AL Division Series"),
    N_("NL Division Series"),
    N_("AL Championship Series"),
    N_("NL Championship Series"),
    N_("World Series"),
]


@lru_cache(maxsize=None)
def get_translations(locale: str):
    if locale == "en":
        return NullTranslations()
    return Translations.load(str(TRANSLATIONS_DIR), [locale])


def template_context(locale: str = DEFAULT_LOCALE) -> dict:
    """Functions every template can use, bound to one locale."""
    t = get_translations(locale)

    def fmt_date(value: date, fmt: str = "EEE, d MMM") -> str:
        text = format_date(value, fmt, locale=locale)
        return text[:1].upper() + text[1:]

    return {
        "locale": locale,
        "_": t.gettext,
        "gettext": t.gettext,
        "ngettext": t.ngettext,
        "fmt_date": fmt_date,
    }
