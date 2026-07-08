from django.db import models


class RideStatus(models.TextChoices):
    SEARCHING = "SEARCHING", "Searching for driver"
    ACCEPTED = "ACCEPTED", "Accepted"
    DRIVER_ARRIVED = "DRIVER_ARRIVED", "Driver arrived"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


# A passenger with a ride in one of these states cannot request another.
ACTIVE_RIDE_STATUSES = [
    RideStatus.SEARCHING,
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_ARRIVED,
    RideStatus.IN_PROGRESS,
]

# A driver assigned to a ride in one of these states cannot accept another.
DRIVER_BUSY_STATUSES = [
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_ARRIVED,
    RideStatus.IN_PROGRESS,
]

# History endpoints return only these.
TERMINAL_RIDE_STATUSES = [
    RideStatus.COMPLETED,
    RideStatus.CANCELLED,
    RideStatus.EXPIRED,
]


class CancelledByRole(models.TextChoices):
    PASSENGER = "PASSENGER", "Passenger"
    DRIVER = "DRIVER", "Driver"
    ADMIN = "ADMIN", "Admin"
    SYSTEM = "SYSTEM", "System"  # search timeout / automatic expiry


class RideEventType(models.TextChoices):
    REQUESTED = "REQUESTED", "Ride requested"
    ACCEPTED = "ACCEPTED", "Driver accepted"
    REJECTED = "REJECTED", "Driver rejected"
    DRIVER_ARRIVED = "DRIVER_ARRIVED", "Driver arrived"
    TRIP_STARTED = "TRIP_STARTED", "Trip started"
    TRIP_COMPLETED = "TRIP_COMPLETED", "Trip completed"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"
    PAYMENT_CLAIMED = "PAYMENT_CLAIMED", "Payment claimed"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED", "Payment confirmed"
