from django.urls import path

from .views import ReverseGeocodeView, RouteView, SuggestView

app_name = "geo"

urlpatterns = [
    path("suggest/", SuggestView.as_view(), name="suggest"),
    path("reverse/", ReverseGeocodeView.as_view(), name="reverse"),
    path("route/", RouteView.as_view(), name="route"),
]
