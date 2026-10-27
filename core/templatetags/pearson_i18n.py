from django import template

from core.i18n import translate

register = template.Library()


@register.simple_tag
def t(text, **kwargs):
    out = translate(text)
    if kwargs:
        try:
            out = out % kwargs
        except (KeyError, ValueError, TypeError):
            pass
    return out


@register.filter
def tr(value):
    return translate(value)
