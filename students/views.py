from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.decorators import student_required
from core.i18n import translate as _t
from core.models import (Achievement, Course, Enrollment, Goal, Grade, Message, PracticeActivity,
                         PracticeSession, Profile, Task, UserAchievement)
from core.stats import bump_week, pct, week_values
from core.utils import safe_next

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _quick_stats(user, profile):
    courses_done = Enrollment.objects.filter(user=user, progress__gte=100).count()
    courses_total = Course.objects.count()
    sessions = PracticeSession.objects.filter(user=user).count()
    certs_total = Achievement.objects.filter(is_certificate=True).count()
    certs_done = UserAchievement.objects.filter(user=user, achievement__is_certificate=True).count()
    return [
        {"label": "Courses Completed", "done": courses_done, "total": courses_total, "percent": pct(courses_done, courses_total)},
        {"label": "Practice Sessions", "done": sessions, "total": profile.practice_goal, "percent": pct(sessions, profile.practice_goal)},
        {"label": "Certificates Earned", "done": certs_done, "total": certs_total, "percent": pct(certs_done, certs_total)},
    ]


@student_required
def dashboard(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    featured = (Enrollment.objects.filter(user=user, course__featured=True)
                .select_related("course").order_by("course__order")[:3])
    tasks = Task.objects.filter(user=user, done=False).select_related("course")[:4]
    week = [{"label": DAYS[i], "percent": v} for i, v in enumerate(week_values(user))]
    return render(request, "students/dashboard.html", {
        "active": "dashboard", "profile": profile, "featured": featured, "tasks": tasks,
        "week": week, "stats": _quick_stats(user, profile),
    })


# ---------- Courses ----------
@student_required
def my_courses(request):
    q = request.GET.get("q", "").strip()
    enrollments = Enrollment.objects.filter(user=request.user).select_related("course").order_by("course__order")
    joined = list(enrollments.values_list("course_id", flat=True))
    available = Course.objects.exclude(id__in=joined)
    if q:
        enrollments = enrollments.filter(course__title__icontains=q)
        available = available.filter(title__icontains=q)
    return render(request, "students/courses.html", {
        "active": "courses", "enrollments": enrollments, "available": available, "q": q,
    })


@student_required
def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    return render(request, "students/course_detail.html", {
        "active": "courses", "course": course, "enrollment": enrollment,
        "activities": PracticeActivity.objects.filter(course=course),
        "tasks": Task.objects.filter(user=request.user, course=course),
        "grades": Grade.objects.filter(user=request.user, course=course),
    })


@require_POST
@student_required
def course_join(request, slug):
    course = get_object_or_404(Course, slug=slug)
    Enrollment.objects.get_or_create(user=request.user, course=course)
    messages.success(request, _t("You joined “%(title)s”.") % {"title": _t(course.title)})
    return redirect("students:course_detail", slug=slug)


# ---------- Practice ----------
PRACTICE_TITLES = {
    "all": "All Practice",
    "speaking": "Speaking Practice",
    "listening": "Listening Practice",
    "writing": "Writing Workshop",
    "quizzes": "Quizzes & Challenges",
}


@student_required
def practice(request, kind="all"):
    if kind not in PRACTICE_TITLES:
        kind = "all"
    activities = PracticeActivity.objects.select_related("course")
    if kind != "all":
        activities = activities.filter(kind=kind)
    recent = PracticeSession.objects.filter(user=request.user).select_related("activity")[:6]
    return render(request, "students/practice.html", {
        "active": "practice", "kind": kind, "title": PRACTICE_TITLES[kind],
        "activities": activities, "recent": recent,
    })


@require_POST
@student_required
def practice_start(request, pk):
    activity = get_object_or_404(PracticeActivity, pk=pk)
    PracticeSession.objects.create(user=request.user, activity=activity)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.add_points(activity.points)
    bump_week(request.user, 15)
    messages.success(request, _t("Great job! “%(title)s” completed (+%(pts)s pts).")
                     % {"title": _t(activity.title), "pts": activity.points})
    return redirect(safe_next(request, "students:practice"))


# ---------- Progress / grades ----------
@student_required
def progress(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    grades = Grade.objects.filter(user=user).select_related("course")
    avg = round(sum(g.percent for g in grades) / len(grades)) if grades else 0
    board = list(Profile.objects.filter(role__iexact="student").select_related("user")
                 .order_by("-points", "user__first_name")[:10])
    rank = Profile.objects.filter(role__iexact="student", points__gt=profile.points).count() + 1
    return render(request, "students/progress.html", {
        "active": "progress", "profile": profile, "grades": grades, "avg": avg,
        "board": board, "rank": rank,
        "enrollments": Enrollment.objects.filter(user=user).select_related("course"),
        "stats": _quick_stats(user, profile),
    })


# ---------- Tasks (homework) ----------
@student_required
def tasks(request):
    items = Task.objects.filter(user=request.user).select_related("course", "assigned_by", "assignment")
    return render(request, "students/tasks.html", {
        "active": "tasks", "open_tasks": [t for t in items if not t.done],
        "done_tasks": [t for t in items if t.done],
    })


@require_POST
@student_required
def task_toggle(request, pk):
    """Vazifani bajarilgan deb belgilash / qaytarish. Tutor vazifasi uchun javob matni ham yuboriladi."""
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if task.score is not None:
        messages.error(request, _t("This task has already been graded."))
        return redirect(safe_next(request, "students:tasks"))
    task.done = not task.done
    if task.done:
        task.submitted_at = timezone.now()
        answer = request.POST.get("answer")
        if answer is not None:
            task.answer = answer.strip()[:5000]
    else:
        task.submitted_at = None
    task.save()
    if task.done and not task.points_awarded:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.add_points(task.reward)
        task.points_awarded = True
        task.save(update_fields=["points_awarded"])
        bump_week(request.user, 20)
        messages.success(request, _t("Task completed (+%(pts)s pts).") % {"pts": task.reward})
    return redirect(safe_next(request, "students:tasks"))


# ---------- Achievements ----------
@student_required
def achievements(request):
    earned = {ua.achievement_id: ua.earned_at for ua in UserAchievement.objects.filter(user=request.user)}
    items = [{"a": a, "earned_at": earned.get(a.id)} for a in Achievement.objects.all()]
    return render(request, "students/achievements.html", {
        "active": "achievements", "items": items, "earned_count": len(earned),
    })


# ---------- Messages ----------
@student_required
def inbox(request):
    return render(request, "students/messages.html", {
        "active": "messages", "items": Message.objects.filter(recipient=request.user),
    })


@student_required
def message_detail(request, pk):
    msg = get_object_or_404(Message, pk=pk, recipient=request.user)
    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=["is_read"])
    return render(request, "students/message_detail.html", {"active": "messages", "msg": msg})


# ---------- Goals ----------
@student_required
def goals(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if title:
            Goal.objects.create(user=request.user, title=title[:150])
            messages.success(request, _t("Goal added."))
        return redirect("students:goals")
    return render(request, "students/goals.html", {
        "active": "dashboard", "goals": Goal.objects.filter(user=request.user),
    })


@require_POST
@student_required
def goal_toggle(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    goal.done = not goal.done
    goal.save()
    return redirect("students:goals")
