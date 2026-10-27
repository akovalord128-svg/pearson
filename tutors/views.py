import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AssignmentForm, GroupForm
from core.decorators import tutor_required
from core.i18n import translate as _t
from core.models import (Assignment, AttendanceRecord, AttendanceSession,
                         Enrollment, Grade, Group, Message, Profile, Task, TutorNote)
from core.stats import monday_of, pct, student_stats, week_values

User = get_user_model()
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def my_students(tutor):
    return (User.objects.filter(study_groups__tutor=tutor).distinct()
            .select_related("profile").order_by("first_name", "username"))


def full_name(u):
    return u.get_full_name() or u.username


# ============ Dashboard ============
@tutor_required
def dashboard(request):
    tutor = request.user
    today = timezone.localdate()
    students = list(my_students(tutor))
    stats = [student_stats(s, tutor) for s in students]

    tasks = Task.objects.filter(assignment__tutor=tutor)
    total, done = tasks.count(), tasks.filter(done=True).count()
    grades = list(Grade.objects.filter(task__assignment__tutor=tutor))
    avg_score = round(sum(g.percent for g in grades) / len(grades)) if grades else None

    kpis = {
        "students": len(students),
        "groups": Group.objects.filter(tutor=tutor).count(),
        "active_assignments": Assignment.objects.filter(tutor=tutor, due_date__gte=today).count(),
        "pending": tasks.filter(done=True, score__isnull=True).count(),
        "completion": pct(done, total),
        "avg_score": avg_score,
    }

    attention = sorted([s for s in stats if s["inactive"] or s["overdue"]],
                       key=lambda s: (-s["overdue"], -(s["days_inactive"] or 999)))[:6]
    top = sorted(stats, key=lambda s: -s["profile"].points)[:5]
    recent = (tasks.filter(done=True).select_related("user", "assignment")
              .order_by("-submitted_at")[:6])

    # Shu haftadagi topshirishlar (kunlar bo'yicha)
    monday = monday_of(today)
    counts = [0] * 7
    for dt in tasks.filter(submitted_at__date__gte=monday).values_list("submitted_at", flat=True):
        counts[timezone.localtime(dt).weekday()] += 1
    mx = max(counts) or 1
    week = [{"label": DAYS[i], "count": c, "percent": round(c * 100 / mx)} for i, c in enumerate(counts)]

    return render(request, "tutors/dashboard.html", {
        "active": "t_dashboard", "kpis": kpis, "attention": attention, "top": top,
        "recent": recent, "week": week,
    })


# ============ Students ============
def _filtered_stats(request):
    tutor = request.user
    qs = my_students(tutor)
    q = request.GET.get("q", "").strip()
    gid = request.GET.get("group", "")
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q))
    if gid.isdigit():
        qs = qs.filter(study_groups__id=int(gid), study_groups__tutor=tutor)
    stats = [student_stats(s, tutor) for s in qs]
    sort = request.GET.get("sort", "name")
    keys = {
        "points": lambda s: -s["profile"].points,
        "completion": lambda s: s["completion"],
        "avg": lambda s: -(s["avg"] if s["avg"] is not None else -1),
        "inactive": lambda s: -(s["days_inactive"] if s["days_inactive"] is not None else 9999),
    }
    if sort in keys:
        stats.sort(key=keys[sort])
    return stats, q, gid, sort


@tutor_required
def students(request):
    stats, q, gid, sort = _filtered_stats(request)
    return render(request, "tutors/students.html", {
        "active": "t_students", "stats": stats, "q": q, "gid": gid, "sort": sort,
        "groups": Group.objects.filter(tutor=request.user),
    })


@tutor_required
def students_export(request):
    stats, *_ = _filtered_stats(request)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="pearson_students.csv"'
    resp.write("\ufeff")
    w = csv.writer(resp, delimiter=";")
    w.writerow([_t("Student"), _t("Username"), _t("Groups"), _t("Level"), _t("Points"), _t("Tasks done"),
                _t("Total tasks"), _t("Completion"), _t("Average grade"), _t("Overdue"),
                _t("Last active"), _t("Days inactive")])
    for s in stats:
        u = s["user"]
        groups = ", ".join(u.study_groups.filter(tutor=request.user).values_list("name", flat=True))
        la = timezone.localtime(s["last_active"]).strftime("%Y-%m-%d %H:%M") if s["last_active"] else "—"
        w.writerow([full_name(u), u.username, groups, s["profile"].level, s["profile"].points, s["done"],
                    s["total"], f'{s["completion"]}%', f'{s["avg"]}%' if s["avg"] is not None else "—",
                    s["overdue"], la, s["days_inactive"] if s["days_inactive"] is not None else "—"])
    return resp


@tutor_required
def student_detail(request, pk):
    tutor = request.user
    student = get_object_or_404(my_students(tutor), pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "note":
            text = request.POST.get("text", "").strip()
            if text:
                TutorNote.objects.create(tutor=tutor, student=student, text=text[:2000])
                messages.success(request, _t("Note saved."))
        elif action == "message":
            subject = request.POST.get("subject", "").strip()
            body = request.POST.get("body", "").strip()
            if subject and body:
                Message.objects.create(recipient=student, author=tutor, sender=full_name(tutor),
                                       subject=subject[:150], body=body)
                messages.success(request, _t("Message sent."))
        return redirect("tutors:student_detail", pk=pk)

    tasks = Task.objects.filter(user=student, assignment__tutor=tutor).select_related("assignment", "course")
    return render(request, "tutors/student_detail.html", {
        "active": "t_students", "student": student, "s": student_stats(student, tutor),
        "tasks": tasks,
        "grades": Grade.objects.filter(user=student, task__assignment__tutor=tutor).select_related("course"),
        "courses": Enrollment.objects.filter(user=student).select_related("course").order_by("course__order"),
        "notes": TutorNote.objects.filter(tutor=tutor, student=student),
        "groups": student.study_groups.filter(tutor=tutor),
        "week": [{"label": DAYS[i], "percent": v} for i, v in enumerate(week_values(student))],
    })


# ============ Groups ============
@tutor_required
def groups(request):
    form = GroupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        g = form.save(commit=False)
        g.tutor = request.user
        g.save()
        messages.success(request, _t("Group created."))
        return redirect("tutors:group_detail", pk=g.pk)
    items = Group.objects.filter(tutor=request.user).annotate(n=Count("students", distinct=True))
    return render(request, "tutors/groups.html", {"active": "t_groups", "groups": items, "form": form})


@tutor_required
def group_detail(request, pk):
    tutor = request.user
    group = get_object_or_404(Group, pk=pk, tutor=tutor)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            ident = request.POST.get("student", "").strip()
            u = User.objects.filter(Q(username__iexact=ident) | Q(email__iexact=ident)).first() if ident else None
            if u is None:
                messages.error(request, _t("Student not found."))
            elif u.profile.is_tutor:
                messages.error(request, _t("This account is a tutor, not a student."))
            else:
                group.students.add(u)
                messages.success(request, _t("Student added to the group."))
        elif action == "remove":
            sid = request.POST.get("student_id", "")
            if sid.isdigit():
                group.students.remove(int(sid))
                messages.success(request, _t("Student removed from the group."))
        elif action == "delete":
            group.delete()
            messages.success(request, _t("Group deleted."))
            return redirect("tutors:groups")
        return redirect("tutors:group_detail", pk=pk)

    members = [student_stats(s, tutor) for s in group.students.select_related("profile").order_by("first_name", "username")]
    return render(request, "tutors/group_detail.html", {
        "active": "t_groups", "group": group, "members": members,
        "assignments": group.assignments.annotate(
            total=Count("tasks"), done=Count("tasks", filter=Q(tasks__done=True))),
        "avg_completion": round(sum(m["completion"] for m in members) / len(members)) if members else 0,
    })


# ============ Assignments ============
@tutor_required
def assignments(request):
    items = list(Assignment.objects.filter(tutor=request.user).select_related("group", "course").annotate(
        total=Count("tasks"),
        done=Count("tasks", filter=Q(tasks__done=True)),
        graded=Count("tasks", filter=Q(tasks__score__isnull=False))))
    for a in items:
        a.percent = pct(a.done, a.total)
    return render(request, "tutors/assignments.html", {"active": "t_assignments", "items": items})


@tutor_required
def assignment_create(request):
    tutor = request.user
    if not Group.objects.filter(tutor=tutor).exists():
        messages.error(request, _t("Create a group first."))
        return redirect("tutors:groups")
    initial = {}
    gid = request.GET.get("group", "")
    if gid.isdigit():
        initial["group"] = int(gid)
    form = AssignmentForm(request.POST or None, tutor=tutor, initial=initial)
    if request.method == "POST" and form.is_valid():
        a = form.save(commit=False)
        a.tutor = tutor
        a.save()
        targets = form.cleaned_data["students"] or a.group.students.all()
        count = 0
        for st in targets:
            Task.objects.create(user=st, assignment=a, assigned_by=tutor, title=a.title,
                                description=a.description, course=a.course, kind=a.kind,
                                minutes=a.minutes, due_date=a.due_date, max_score=a.max_score)
            Message.objects.create(recipient=st, author=tutor, sender=full_name(tutor),
                                   subject=f"📝 {a.title}",
                                   body=f"{a.description}\n\n⏰ {a.due_date:%Y-%m-%d}".strip())
            count += 1
        messages.success(request, _t("Assignment sent to %(n)s students.") % {"n": count})
        return redirect("tutors:assignment_detail", pk=a.pk)
    return render(request, "tutors/assignment_form.html", {"active": "t_assignments", "form": form})


@tutor_required
def assignment_detail(request, pk):
    a = get_object_or_404(Assignment.objects.select_related("group", "course"), pk=pk, tutor=request.user)
    rows = list(a.tasks.select_related("user").order_by("user__first_name", "user__username"))
    done = sum(1 for t in rows if t.done)
    graded = [t for t in rows if t.score is not None]
    return render(request, "tutors/assignment_detail.html", {
        "active": "t_assignments", "a": a, "rows": rows, "done": done, "total": len(rows),
        "percent": pct(done, len(rows)),
        "avg": round(sum(t.score * 100 / (t.max_score or 100) for t in graded) / len(graded)) if graded else None,
    })


@require_POST
@tutor_required
def assignment_delete(request, pk):
    a = get_object_or_404(Assignment, pk=pk, tutor=request.user)
    a.delete()
    messages.success(request, _t("Assignment deleted."))
    return redirect("tutors:assignments")


@require_POST
@tutor_required
def task_grade(request, pk):
    task = get_object_or_404(Task.objects.select_related("assignment", "user"), pk=pk, assignment__tutor=request.user)
    back = redirect("tutors:assignment_detail", pk=task.assignment_id)
    if not task.done:
        messages.error(request, _t("The student has not submitted this task yet."))
        return back
    raw = request.POST.get("score", "").strip()
    if not raw.isdigit() or int(raw) > task.max_score:
        messages.error(request, _t("Enter a score between 0 and %(max)s.") % {"max": task.max_score})
        return back
    task.score = int(raw)
    task.feedback = request.POST.get("feedback", "").strip()[:2000]
    task.save(update_fields=["score", "feedback"])
    Grade.objects.update_or_create(task=task, defaults=dict(
        user=task.user, course=task.course, title=task.title, score=task.score,
        max_score=task.max_score, date=timezone.localdate()))
    Message.objects.create(recipient=task.user, author=request.user, sender=full_name(request.user),
                           subject=f"✅ {task.title}",
                           body=f"{task.score}/{task.max_score}\n\n{task.feedback}".strip())
    messages.success(request, _t("Grade saved."))
    return back


# ============ Messages ============
@tutor_required
def compose(request):
    tutor = request.user
    groups_qs = Group.objects.filter(tutor=tutor)
    studs = list(my_students(tutor))
    if request.method == "POST":
        target = request.POST.get("target", "")
        subject = request.POST.get("subject", "").strip()
        body = request.POST.get("body", "").strip()
        recipients = []
        kind, _, ident = target.partition(":")
        if kind == "g" and ident.isdigit():
            g = groups_qs.filter(pk=int(ident)).first()
            recipients = list(g.students.all()) if g else []
        elif kind == "s" and ident.isdigit():
            recipients = [s for s in studs if s.pk == int(ident)]
        if not (subject and body and recipients):
            messages.error(request, _t("Choose a recipient and fill in the subject and message."))
        else:
            for r in recipients:
                Message.objects.create(recipient=r, author=tutor, sender=full_name(tutor),
                                       subject=subject[:150], body=body)
            messages.success(request, _t("Message sent to %(n)s students.") % {"n": len(recipients)})
        return redirect("tutors:compose")
    sent = Message.objects.filter(author=tutor).select_related("recipient")[:15]
    return render(request, "tutors/compose.html", {
        "active": "t_messages", "groups": groups_qs, "students": studs, "sent": sent,
    })


# ============ Attendance ============
@tutor_required
def attendance_list(request):
    """Barcha davomat sessiyalari ro'yxati."""
    tutor = request.user
    gid = request.GET.get("group", "")
    sessions_qs = AttendanceSession.objects.filter(tutor=tutor).select_related("group").annotate(
        total=Count("records"),
        present=Count("records", filter=Q(records__status="present")),
        late=Count("records", filter=Q(records__status="late")),
        absent=Count("records", filter=Q(records__status="absent")),
        excused=Count("records", filter=Q(records__status="excused")),
    )
    if gid.isdigit():
        sessions_qs = sessions_qs.filter(group_id=int(gid))
    groups_qs = Group.objects.filter(tutor=tutor)
    return render(request, "tutors/attendance_list.html", {
        "active": "t_attendance",
        "sessions": sessions_qs,
        "groups": groups_qs,
        "gid": gid,
    })


@tutor_required
def attendance_create(request):
    """Yangi davomat sessiyasi yaratish."""
    tutor = request.user
    if not Group.objects.filter(tutor=tutor).exists():
        messages.error(request, _t("Create a group first."))
        return redirect("tutors:groups")

    groups_qs = Group.objects.filter(tutor=tutor)
    selected_group = None
    gid = request.GET.get("group", "") or request.POST.get("group", "")
    if gid.isdigit():
        selected_group = groups_qs.filter(pk=int(gid)).first()

    if request.method == "POST":
        group_id = request.POST.get("group", "")
        date_str = request.POST.get("date", "")
        topic = request.POST.get("topic", "").strip()
        try:
            from datetime import date as _date
            parsed_date = _date.fromisoformat(date_str)
        except ValueError:
            messages.error(request, _t("Invalid date."))
            return redirect("tutors:attendance_create")

        group = get_object_or_404(Group, pk=group_id, tutor=tutor)
        session, created = AttendanceSession.objects.get_or_create(
            tutor=tutor, group=group, date=parsed_date,
            defaults={"topic": topic},
        )
        if not created:
            session.topic = topic
            session.save(update_fields=["topic"])
            messages.warning(request, _t("A session for this group and date already exists. Editing it."))
        else:
            # Guruh a'zolari uchun "present" default yozuv yaratish
            for student in group.students.all():
                AttendanceRecord.objects.get_or_create(session=session, student=student,
                                                       defaults={"status": "present"})
        return redirect("tutors:attendance_detail", pk=session.pk)

    today = timezone.localdate().isoformat()
    return render(request, "tutors/attendance_create.html", {
        "active": "t_attendance",
        "groups": groups_qs,
        "selected_group": selected_group,
        "today": today,
    })


@tutor_required
def attendance_detail(request, pk):
    """Bitta sessiya: o'quvchilar davomati kiritish/tahrirlash."""
    tutor = request.user
    session = get_object_or_404(AttendanceSession, pk=pk, tutor=tutor)
    students = session.group.students.all().order_by("first_name", "username")

    if request.method == "POST":
        # Har bir o'quvchi uchun status va note o'qib yozamiz
        for student in students:
            status = request.POST.get(f"status_{student.pk}", "absent")
            note = request.POST.get(f"note_{student.pk}", "").strip()[:200]
            if status not in ("present", "absent", "late", "excused"):
                status = "absent"
            AttendanceRecord.objects.update_or_create(
                session=session, student=student,
                defaults={"status": status, "note": note},
            )
        # Mavzuni ham yangilaymiz
        topic = request.POST.get("topic", "").strip()
        session.topic = topic
        session.save(update_fields=["topic"])
        messages.success(request, _t("Attendance saved."))
        return redirect("tutors:attendance_detail", pk=pk)

    # Yozuvlarni dict sifatida tayyorlaymiz
    records = {r.student_id: r for r in session.records.all()}
    rows = []
    for student in students:
        rec = records.get(student.pk)
        rows.append({
            "student": student,
            "status": rec.status if rec else "present",
            "note": rec.note if rec else "",
        })

    status_counts = {s: sum(1 for r in rows if r["status"] == s)
                     for s in ("present", "late", "absent", "excused")}
    total = len(rows)
    attendance_pct = pct(status_counts["present"] + status_counts["late"], total)

    return render(request, "tutors/attendance_detail.html", {
        "active": "t_attendance",
        "session": session,
        "rows": rows,
        "status_counts": status_counts,
        "total": total,
        "attendance_pct": attendance_pct,
    })


@require_POST
@tutor_required
def attendance_delete(request, pk):
    """Sessiyani o'chirish."""
    session = get_object_or_404(AttendanceSession, pk=pk, tutor=request.user)
    session.delete()
    messages.success(request, _t("Session deleted."))
    return redirect("tutors:attendance_list")


@tutor_required
def attendance_student(request, pk):
    """Bitta o'quvchining barcha davomati tarixi."""
    tutor = request.user
    student = get_object_or_404(
        get_user_model().objects.filter(study_groups__tutor=tutor).distinct(), pk=pk)
    records = (AttendanceRecord.objects
               .filter(session__tutor=tutor, student=student)
               .select_related("session", "session__group")
               .order_by("-session__date"))
    total = records.count()
    present = records.filter(status__in=("present", "late")).count()
    att_pct = pct(present, total)
    return render(request, "tutors/attendance_student.html", {
        "active": "t_students",
        "student": student,
        "records": records,
        "total": total,
        "present": present,
        "att_pct": att_pct,
    })
