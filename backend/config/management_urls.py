"""Admin/staff API — /api/v1/management/ (distinct from Django's /admin/ site).

One route table for the whole management surface; views live in their
domain apps. Rides and payments management arrive in Modules 6-7.
"""
from django.urls import path

from apps.accounts.management_views import UserListView, VerifyNinView
from apps.drivers.management_views import (
    ApproveDriverView,
    DriverDetailView,
    DriverListView,
    RejectDriverView,
)
from apps.commissions.management_views import (
    CommissionListView,
    CommissionSummaryView,
    RemitCommissionView,
    SettleDriverView,
)
from apps.payments.management_views import PaymentAdminDetailView, PaymentAdminListView
from apps.pricing.management_views import FareSettingListCreateView
from apps.rides.management_views import RideAdminDetailView, RideAdminListView

app_name = "management"

urlpatterns = [
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/verify-nin/", VerifyNinView.as_view(), name="user-verify-nin"),
    path("drivers/", DriverListView.as_view(), name="driver-list"),
    path("drivers/<int:pk>/", DriverDetailView.as_view(), name="driver-detail"),
    path("drivers/<int:pk>/approve/", ApproveDriverView.as_view(), name="driver-approve"),
    path("drivers/<int:pk>/reject/", RejectDriverView.as_view(), name="driver-reject"),
    path("rides/", RideAdminListView.as_view(), name="ride-list"),
    path("rides/<int:pk>/", RideAdminDetailView.as_view(), name="ride-detail"),
    path("payments/", PaymentAdminListView.as_view(), name="payment-list"),
    path("payments/<int:pk>/", PaymentAdminDetailView.as_view(), name="payment-detail"),
    path("fare-settings/", FareSettingListCreateView.as_view(), name="fare-setting-list"),
    path("commissions/", CommissionListView.as_view(), name="commission-list"),
    path("commissions/summary/", CommissionSummaryView.as_view(), name="commission-summary"),
    path("commissions/<int:pk>/remit/", RemitCommissionView.as_view(), name="commission-remit"),
    path("commissions/settle-driver/", SettleDriverView.as_view(), name="commission-settle-driver"),
]
