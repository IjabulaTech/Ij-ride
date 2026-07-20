from django.urls import path

from .views import MySupportThreadView

app_name = "support"

urlpatterns = [
    path("messages/", MySupportThreadView.as_view(), name="my-messages"),
]
