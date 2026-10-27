"""O'quvchi statistikasi (o'quvchi paneli ham, tutor paneli ham shu yerdan foydalanadi)."""
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from .models import (Enrollment, Grade, PracticeSession, Profile, Task, WeeklyProgress)

INACTIVE_DAYS = 7


def monday_of(d):
    return d - timedelta(days=d.weekday())


def bump_week(user, amount=15):
    """Bugungi kun faolligini oshiradi (Weekly Progress grafigi uchun)."""
    today = timezone.localdate()
    obj, _ = WeeklyProgress.objects.get_or_create(user=user, week=monday_of(today), weekday=today.weekday())
    obj.percent = min(100, obj.percent + amount)
    obj.save()


def week_values(user):
    monday = monday_of(timezone.localdate())
    rows = {w.weekday: w.percent for w in WeeklyProgress.objects.filter(user=user, week=monday)}
    return [rows.get(i, 0) for i in range(7)]


def pct(done, total):
    return min(100, round(done * 100 / total)) if total else 0


def last_active(user):
    stamps = [user.last_login]
    stamps.append(PracticeSession.objects.filter(user=user).aggregate(m=Max("created"))["m"])
    stamps.append(Task.objects.filter(user=user).aggregate(m=Max("submitted_at"))["m"])
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None


def student_stats(user, tutor=None):
    """Bitta o'quvchi uchun umumiy ko'rsatkichlar. tutor berilsa — faqat shu tutor bergan vazifalar."""
    tasks = Task.objects.filter(user=user)
    if tutor is not None:
        tasks = tasks.filter(assignment__tutor=tutor)
    tasks = list(tasks)
    total = len(tasks)
    done = sum(1 for t in tasks if t.done)
    overdue = sum(1 for t in tasks if t.is_overdue)
    pending_review = sum(1 for t in tasks if t.done and t.score is None)

    grades = Grade.objects.filter(user=user)
    if tutor is not None:
        grades = grades.filter(task__assignment__tutor=tutor)
    grades = list(grades)
    avg = round(sum(g.percent for g in grades) / len(grades)) if grades else None

    la = last_active(user)
    days_inactive = (timezone.now() - la).days if la else None
    profile = getattr(user, "profile", None) or Profile.objects.get_or_create(user=user)[0]
    return {
        "user": user, "profile": profile,
        "total": total, "done": done, "overdue": overdue, "pending_review": pending_review,
        "completion": pct(done, total), "avg": avg, "grades_count": len(grades),
        "last_active": la, "days_inactive": days_inactive,
        "inactive": days_inactive is None or days_inactive >= INACTIVE_DAYS,
        "sessions": PracticeSession.objects.filter(user=user).count(),
    }


def student_courses(user):
    return Enrollment.objects.filter(user=user).select_related("course").order_by("course__order")
