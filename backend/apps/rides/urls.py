from django.urls import path

from apps.payments.views import ClaimPaymentView, ConfirmPaymentView

from .views import (
    AcceptRideView,
    ActiveRideView,
    ArrivedRideView,
    CancelRideView,
    CompleteRideView,
    OpenRidesView,
    RejectRideView,
    RideDetailView,
    RideEstimateView,
    RideListCreateView,
    StartRideView,
)

app_name = "rides"

urlpatterns = [
    path("", RideListCreateView.as_view(), name="list-create"),
    path("estimate/", RideEstimateView.as_view(), name="estimate"),
    path("active/", ActiveRideView.as_view(), name="active"),
    path("open/", OpenRidesView.as_view(), name="open"),
    path("<int:pk>/", RideDetailView.as_view(), name="detail"),
    path("<int:pk>/accept/", AcceptRideView.as_view(), name="accept"),
    path("<int:pk>/reject/", RejectRideView.as_view(), name="reject"),
    path("<int:pk>/arrived/", ArrivedRideView.as_view(), name="arrived"),
    path("<int:pk>/start/", StartRideView.as_view(), name="start"),
    path("<int:pk>/complete/", CompleteRideView.as_view(), name="complete"),
    path("<int:pk>/cancel/", CancelRideView.as_view(), name="cancel"),
    path("<int:pk>/payment/claim/", ClaimPaymentView.as_view(), name="payment-claim"),
    path("<int:pk>/payment/confirm/", ConfirmPaymentView.as_view(), name="payment-confirm"),
]
