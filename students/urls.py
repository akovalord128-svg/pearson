from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("courses/", views.my_courses, name="courses"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("courses/<slug:slug>/join/", views.course_join, name="course_join"),
    path("practice/", views.practice, name="practice"),
    path("practice/start/<int:pk>/", views.practice_start, name="practice_start"),
    path("practice/<str:kind>/", views.practice, name="practice_kind"),
    path("progress/", views.progress, name="progress"),
    path("tasks/", views.tasks, name="tasks"),
    path("tasks/<int:pk>/toggle/", views.task_toggle, name="task_toggle"),
    path("achievements/", views.achievements, name="achievements"),
    path("messages/", views.inbox, name="messages"),
    path("messages/<int:pk>/", views.message_detail, name="message_detail"),
    path("goals/", views.goals, name="goals"),
    path("goals/<int:pk>/toggle/", views.goal_toggle, name="goal_toggle"),
]
