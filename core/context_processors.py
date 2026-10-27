from .i18n import LANGS


def globals(request):
    ctx = {"LANGS": LANGS, "LANG": getattr(request, "LANG", "uz")}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        ctx["unread_count"] = user.inbox.filter(is_read=False).count()
        profile = getattr(user, "profile", None)
        ctx["is_tutor"] = bool(profile and profile.is_tutor)
        ctx["role_label"] = profile.role_label if profile else "Student"
    return ctx
