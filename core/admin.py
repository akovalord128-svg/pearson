from django.contrib import admin
from .models import (
    Profile, Course, Enrollment, PracticeActivity, PracticeSession,
    Group, Assignment, Task, WeeklyProgress, Grade, Achievement,
    UserAchievement, Message, Goal, TutorNote,
    AttendanceSession, AttendanceRecord,
)

admin.site.site_header = "Pearson Technikum UZ — Admin"

# Oddiy ro'yxatdan o'tkaziladigan modellar (Maxsus Admin klassi kerak bo'lmaganlar)
admin.site.register(Profile)
admin.site.register(Enrollment)
admin.site.register(PracticeSession)
admin.site.register(WeeklyProgress)
admin.site.register(UserAchievement)
admin.site.register(Group)
admin.site.register(Assignment)
admin.site.register(TutorNote)


# Maxsus ko'rinish va filtrga ega modellar (@admin.register yordamida)
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "featured", "is_club", "order")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(PracticeActivity)
class PracticeActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "minutes", "points")
    list_filter = ("kind",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "kind", "due_date", "done")
    list_filter = ("kind", "done")


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "title", "score", "max_score", "date")


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "points", "is_certificate")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "recipient", "sender", "is_read", "created")


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "done")


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("group", "date", "topic", "tutor")
    list_filter = ("group", "date")
    inlines = [AttendanceRecordInline]