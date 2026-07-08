"""Forms for the Django built-in admin (the API never uses these)."""
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("phone", "role")


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
