"""Oddiy, lekin to'liq 3 tilli tizim (uz / ru / en).

* Kalit — inglizcha matn. Tarjimalar core/translations.py da.
* Shablonda:  {% load pearson_i18n %}  {% t "Dashboard" %}   yoki   {{ course.title|tr }}
* Python kodida:  from core.i18n import translate
"""
import threading

from .translations import TRANSLATIONS

LANGS = [("uz", "UZ", "O‘zbekcha"), ("ru", "RU", "Русский"), ("en", "EN", "English")]
VALID = {code for code, _, _ in LANGS}
DEFAULT_LANG = "uz"

_local = threading.local()


def set_lang(lang):
    _local.lang = lang if lang in VALID else DEFAULT_LANG


def get_lang():
    return getattr(_local, "lang", DEFAULT_LANG)


def translate(text, lang=None):
    lang = lang or get_lang()
    if lang == "en" or not text or not isinstance(text, str):
        return text
    entry = TRANSLATIONS.get(text)
    if entry:
        return entry.get(lang, text)
    return text
