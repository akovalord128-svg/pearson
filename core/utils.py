from django.utils.http import url_has_allowed_host_and_scheme


def safe_next(request, default):
    """POST ichidagi 'next' qiymatini xavfsiz tekshiradi (open redirect'dan himoya)."""
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return default
