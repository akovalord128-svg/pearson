from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from core.i18n import translate as _t


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "placeholder": _t("Email address or username"), "autofocus": True, "autocomplete": "username"})
        self.fields["password"].widget.attrs.update({
            "placeholder": _t("Password"), "autocomplete": "current-password"})


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    role = forms.ChoiceField(choices=[("student", "Student"), ("tutor", "Tutor")], initial="student",
                             widget=forms.RadioSelect)
    tutor_code = forms.CharField(required=False)

    field_order = ["role", "full_name", "email", "username", "password1", "password2", "tutor_code"]

    class Meta:
        model = User
        fields = ("email", "username")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ph = {"full_name": "Full name", "email": "Email address", "username": "Username",
              "password1": "Password", "password2": "Confirm password", "tutor_code": "Tutor access code"}
        for name, text in ph.items():
            self.fields[name].widget.attrs["placeholder"] = _t(text)
        for f in ("username", "password1", "password2"):
            self.fields[f].help_text = ""

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_t("This email is already registered."))
        return email

    def clean(self):
        data = super().clean()
        if data.get("role") == "tutor":
            code = (data.get("tutor_code") or "").strip()
            if code != settings.TUTOR_INVITE_CODE:
                self.add_error("tutor_code", _t("Wrong tutor access code."))
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        parts = self.cleaned_data["full_name"].strip().split(None, 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
        if commit:
            user.save()
            profile = user.profile  # signal orqali yaratilgan
            profile.role = self.cleaned_data["role"]
            profile.save()
        return user
