from django.urls import path

from . import views as v

app_name = "tutors"

urlpatterns = [
    path("", v.dashboard, name="dashboard"),
    path("students/", v.students, name="students"),
    path("students/export/", v.students_export, name="students_export"),
    path("students/<int:pk>/", v.student_detail, name="student_detail"),
    path("students/<int:pk>/attendance/", v.attendance_student, name="attendance_student"),
    path("groups/", v.groups, name="groups"),
    path("groups/<int:pk>/", v.group_detail, name="group_detail"),
    path("assignments/", v.assignments, name="assignments"),
    path("assignments/new/", v.assignment_create, name="assignment_create"),
    path("assignments/<int:pk>/", v.assignment_detail, name="assignment_detail"),
    path("assignments/<int:pk>/delete/", v.assignment_delete, name="assignment_delete"),
    path("tasks/<int:pk>/grade/", v.task_grade, name="task_grade"),
    path("messages/", v.compose, name="compose"),
    # Davomat
    path("attendance/", v.attendance_list, name="attendance_list"),
    path("attendance/new/", v.attendance_create, name="attendance_create"),
    path("attendance/<int:pk>/", v.attendance_detail, name="attendance_detail"),
    path("attendance/<int:pk>/delete/", v.attendance_delete, name="attendance_delete"),
]

