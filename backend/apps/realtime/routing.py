"""WebSocket URL patterns, imported by config/asgi.py."""
from django.urls import path

from .consumers import RideConsumer

websocket_urlpatterns = [
    path("ws/rides/", RideConsumer.as_asgi()),
]
