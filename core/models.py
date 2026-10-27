import secrets
import string

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.dateformat import format as date_format

from .i18n import translate

User = settings.AUTH_USER_MODEL

ICON_CHOICES = [
    ("book-open", "Book"), ("laptop", "Laptop"), ("bulb", "Bulb"), ("mic", "Microphone"),
    ("headphones", "Headphones"), ("pencil", "Pencil"), ("trophy", "Trophy"),
    ("certificate", "Certificate"), ("star", "Star"),
]
COLOR_CHOICES = [
    ("teal", "Teal"), ("blue", "Blue"), ("purple", "Purple"), ("green", "Green"), ("orange", "Orange"),
]
TASK_KINDS = [
    ("speaking", "Speaking"), ("listening", "Listening"), ("writing", "Writing"),
    ("digital", "Digital Skills"), ("quiz", "Quiz"), ("homework", "Homework"),
]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    points = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    level_points = models.PositiveIntegerField(default=0, help_text="Joriy darajadagi ball")
    level_target = models.PositiveIntegerField(default=500, help_text="Keyingi darajagacha kerakli ball")
    practice_goal = models.PositiveIntegerField(default=20, help_text="Haftalik mashq maqsadi")
    role = models.CharField(max_length=30, default="student", help_text="student yoki tutor")

    def __str__(self):
        return f"{self.user} [{self.role}] ({self.points} pts)"

    @property
    def is_tutor(self):
        return (self.role or "").strip().lower() == "tutor"

    @property
    def role_label(self):
        return "Tutor" if self.is_tutor else "Student"

    @property
    def level_percent(self):
        return min(100, round(self.level_points * 100 / self.level_target)) if self.level_target else 0

    def add_points(self, pts):
        self.points += pts
        self.level_points += pts
        while self.level_points >= self.level_target:
            self.level_points -= self.level_target
            self.level += 1
            self.level_target += 500
        self.save()


class Course(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    subtitle = models.CharField(max_length=150, blank=True, help_text="Masalan: Reading • Writing • Speaking")
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default="book-open")
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default="blue")
    featured = models.BooleanField(default=False, help_text="Dashboardda katta kartochka sifatida chiqadi")
    is_club = models.BooleanField(default=False, help_text="To'garak (club)")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    progress = models.PositiveIntegerField(default=0)
    milestone = models.PositiveIntegerField(default=1, help_text="Keyingi milestone (Level)")

    class Meta:
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user} → {self.course} ({self.progress}%)"


class PracticeActivity(models.Model):
    KINDS = [
        ("speaking", "Speaking Practice"), ("listening", "Listening Practice"),
        ("writing", "Writing Workshop"), ("quizzes", "Quizzes & Challenges"),
    ]
    kind = models.CharField(max_length=12, choices=KINDS)
    title = models.CharField(max_length=120)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL)
    minutes = models.PositiveIntegerField(default=15)
    points = models.PositiveIntegerField(default=10)
    description = models.CharField(max_length=250, blank=True)

    class Meta:
        verbose_name_plural = "practice activities"
        ordering = ["kind", "title"]

    def __str__(self):
        return self.title


class PracticeSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="practice_sessions")
    activity = models.ForeignKey(PracticeActivity, on_delete=models.CASCADE)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created"]


class Group(models.Model):
    """Tutorning guruhi (sinfi). O'quvchilar tutor qo'shishi yoki guruh kodi orqali kiradi."""
    name = models.CharField(max_length=100)
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tutor_groups")
    students = models.ManyToManyField(User, blank=True, related_name="study_groups")
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL)
    code = models.CharField(max_length=8, unique=True, blank=True)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            alphabet = string.ascii_uppercase + string.digits
            while True:
                code = "".join(secrets.choice(alphabet) for _ in range(6))
                if not Group.objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)


class Assignment(models.Model):
    """Tutor bergan vazifa. Guruh a'zolari (yoki tanlangan o'quvchilar) uchun Task yaratiladi."""
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assignments")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=10, choices=TASK_KINDS, default="homework")
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL)
    minutes = models.PositiveIntegerField(default=30)
    points = models.PositiveIntegerField(default=20)
    max_score = models.PositiveIntegerField(default=100)
    due_date = models.DateField()
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title


class Task(models.Model):
    ICONS = {"speaking": ("mic", "teal"), "listening": ("headphones", "blue"), "writing": ("pencil", "purple"),
             "digital": ("laptop", "blue"), "quiz": ("bulb", "purple"), "homework": ("book-open", "teal")}

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=10, choices=TASK_KINDS, default="homework")
    minutes = models.PositiveIntegerField(default=15)
    due_date = models.DateField()
    done = models.BooleanField(default=False)
    # Tutor bergan vazifalar uchun
    assignment = models.ForeignKey(Assignment, null=True, blank=True, on_delete=models.CASCADE, related_name="tasks")
    assigned_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="given_tasks")
    answer = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(null=True, blank=True)
    max_score = models.PositiveIntegerField(default=100)
    feedback = models.TextField(blank=True)
    points_awarded = models.BooleanField(default=False)

    class Meta:
        ordering = ["done", "due_date", "id"]

    def __str__(self):
        return self.title

    @property
    def icon(self):
        return self.ICONS.get(self.kind, ("book-open", "teal"))[0]

    @property
    def color(self):
        return self.ICONS.get(self.kind, ("book-open", "teal"))[1]

    @property
    def reward(self):
        return self.assignment.points if self.assignment_id else 5

    @property
    def is_overdue(self):
        return (not self.done) and self.due_date < timezone.localdate()

    @property
    def status(self):
        if self.score is not None:
            return "graded"
        if self.done:
            return "submitted"
        if self.is_overdue:
            return "overdue"
        return "todo"

    @property
    def due_label(self):
        today = timezone.localdate()
        if self.due_date == today:
            return translate("Today")
        if (self.due_date - today).days == 1:
            return translate("Tomorrow")
        return date_format(self.due_date, "M j")


class WeeklyProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="weekly")
    week = models.DateField(default=timezone.localdate, help_text="Haftaning dushanba kuni")
    weekday = models.PositiveSmallIntegerField(help_text="0=Mon … 6=Sun")
    percent = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("user", "week", "weekday")
        ordering = ["week", "weekday"]


class Grade(models.Model):
    """Baholar (PPTX: 'baholarni ko'rishingiz')."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="grades")
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=120)
    score = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField(default=100)
    date = models.DateField(default=timezone.localdate)
    task = models.OneToOneField(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name="grade_record")

    class Meta:
        ordering = ["-date", "-id"]

    @property
    def percent(self):
        return round(self.score * 100 / self.max_score) if self.max_score else 0


class Achievement(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=250, blank=True)
    points = models.PositiveIntegerField(default=50)
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default="trophy")
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default="orange")
    is_certificate = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "achievement")


class Message(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="inbox")
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_messages")
    sender = models.CharField(max_length=100, default="Pearson Team")
    subject = models.CharField(max_length=150)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.subject


class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="goals")
    title = models.CharField(max_length=150)
    done = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["done", "-created"]


class TutorNote(models.Model):
    """Tutorning o'quvchi haqidagi shaxsiy yozuvi (o'quvchi ko'rmaydi)."""
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes_written")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes_about")
    text = models.TextField()
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created"]


class AttendanceSession(models.Model):
    """Tutor tomonidan yaratilgan davomat sessiyasi (dars sanasi)."""
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance_sessions")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="attendance_sessions")
    date = models.DateField(default=timezone.localdate)
    topic = models.CharField(max_length=200, blank=True, help_text="Dars mavzusi (ixtiyoriy)")
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date", "-created"]
        unique_together = ("tutor", "group", "date")

    def __str__(self):
        return f"{self.group.name} – {self.date}"


ATTENDANCE_STATUS = [
    ("present", "Present"),
    ("absent", "Absent"),
    ("late", "Late"),
    ("excused", "Excused"),
]


class AttendanceRecord(models.Model):
    """Bitta o'quvchining bitta sessiya uchun davomat yozuvi."""
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="records")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance_records")
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default="present")
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("session", "student")

    def __str__(self):
        return f"{self.student} – {self.session} – {self.status}"
