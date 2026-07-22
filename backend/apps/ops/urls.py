from django.urls import path

from .views import MaintenanceStatusView

app_name = "ops"

urlpatterns = [
    path("status/", MaintenanceStatusView.as_view(), name="status"),
]
