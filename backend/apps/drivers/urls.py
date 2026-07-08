from django.urls import path

from .views import (
    MyAvailabilityView,
    MyDriverProfileView,
    MyEarningsView,
    MyLocationView,
    MyVehicleView,
)

app_name = "drivers"

urlpatterns = [
    path("me/profile/", MyDriverProfileView.as_view(), name="my-profile"),
    path("me/vehicle/", MyVehicleView.as_view(), name="my-vehicle"),
    path("me/availability/", MyAvailabilityView.as_view(), name="my-availability"),
    path("me/location/", MyLocationView.as_view(), name="my-location"),
    path("me/earnings/", MyEarningsView.as_view(), name="my-earnings"),
]
