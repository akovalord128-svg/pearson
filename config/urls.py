from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("student/", include("students.urls")),
    path("tutor/", include("tutors.urls")),
    path("", include("core.urls")),
]
