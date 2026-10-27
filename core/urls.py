from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("lang/", views.set_language, name="set_language"),
    path("settings/", views.settings_view, name="settings"),
]
