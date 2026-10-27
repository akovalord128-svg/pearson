"""Rol bo'yicha kirish: o'quvchi sahifalari faqat o'quvchilarga, tutor sahifalari faqat tutorlarga."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .i18n import translate as _t
from .models import Profile


def _role_required(view, want_tutor):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if profile.is_tutor != want_tutor:
            if want_tutor:
                messages.error(request, _t("This page is for tutors only."))
            return redirect("core:home")
        return view(request, *args, **kwargs)
    return login_required(wrapper)


def student_required(view):
    return _role_required(view, want_tutor=False)


def tutor_required(view):
    return _role_required(view, want_tutor=True)
