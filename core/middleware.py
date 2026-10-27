from django.utils import translation

from .i18n import DEFAULT_LANG, VALID, set_lang


class LangMiddleware:
    """Tilni cookie'dan oladi (uz / ru / en) va Django'ning o'z tarjimalarini ham yoqadi."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.COOKIES.get("lang", DEFAULT_LANG)
        if lang not in VALID:
            lang = DEFAULT_LANG
        set_lang(lang)
        translation.activate(lang)
        request.LANG = lang
        try:
            return self.get_response(request)
        finally:
            translation.deactivate()
