from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ProfileForm
from .i18n import VALID, translate as _t
from .models import Group, Profile
from .utils import safe_next


@login_required
def home(request):
    """Kirgandan keyin rolga qarab kerakli panelga yo'naltiradi."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return redirect("tutors:dashboard" if profile.is_tutor else "students:dashboard")


@require_POST
def set_language(request):
    """Til tugmasi (UZ / RU / EN) — cookie'ga yozadi."""
    lang = request.POST.get("lang")
    response = redirect(safe_next(request, "/"))
    if lang in VALID:
        response.set_cookie("lang", lang, max_age=365 * 24 * 3600, samesite="Lax")
    return response


@login_required
def settings_view(request):
    """Profil va parol — o'quvchi ham, tutor ham shu sahifadan foydalanadi."""
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    profile_form = ProfileForm(instance=user)
    password_form = PasswordChangeForm(user)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "password":
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, _t("Password updated."))
                return redirect("core:settings")
        elif action == "join_group" and not profile.is_tutor:
            code = request.POST.get("code", "").strip().upper()
            group = Group.objects.filter(code=code).first()
            if group:
                group.students.add(user)
                messages.success(request, _t("You joined the group “%(name)s”.") % {"name": group.name})
            else:
                messages.error(request, _t("Group code not found."))
            return redirect("core:settings")
        else:
            profile_form = ProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, _t("Profile updated."))
                return redirect("core:settings")
    return render(request, "core/settings.html", {
        "active": "settings", "profile_form": profile_form, "password_form": password_form,
        "my_groups": [] if profile.is_tutor else user.study_groups.select_related("tutor"),
    })
