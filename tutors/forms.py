from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from core.i18n import translate as _t
from core.models import Assignment, Course, Group


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ("name", "course")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].required = False
        self.fields["course"].empty_label = "—"
        self.fields["name"].widget.attrs["placeholder"] = _t("Group name")


class AssignmentForm(forms.ModelForm):
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(), required=False, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Assignment
        fields = ("group", "title", "description", "kind", "course", "minutes", "points", "max_score", "due_date")
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, tutor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tutor = tutor
        self.fields["group"].queryset = Group.objects.filter(tutor=tutor)
        self.fields["group"].empty_label = None
        self.fields["course"].queryset = Course.objects.all()
        self.fields["course"].required = False
        self.fields["course"].empty_label = "—"
        self.fields["students"].queryset = (
            User.objects.filter(study_groups__tutor=tutor).distinct().order_by("first_name", "username"))
        self.fields["students"].label_from_instance = lambda u: u.get_full_name() or u.username
        self.fields["kind"].choices = [(k, _t(v)) for k, v in self.fields["kind"].choices]
        self.fields["title"].widget.attrs["placeholder"] = _t("Assignment title")

    def clean_due_date(self):
        d = self.cleaned_data["due_date"]
        if d < timezone.localdate():
            raise forms.ValidationError(_t("Due date cannot be in the past."))
        return d

    def clean(self):
        data = super().clean()
        group, students = data.get("group"), data.get("students")
        if group and students:
            member_ids = set(group.students.values_list("id", flat=True))
            if any(s.id not in member_ids for s in students):
                self.add_error("students", _t("Selected students must belong to the chosen group."))
        return data
