from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import Garden, GardenMembership, UserProfile


def ensure_user_workspace(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"display_name": user.get_full_name() or user.email.split("@")[0]},
    )
    garden = Garden.objects.filter(owner=user).first()
    if garden is None:
        garden = Garden.objects.create(owner=user)
    GardenMembership.objects.get_or_create(garden=garden, user=user, defaults={"role": GardenMembership.Role.OWNER})
    return profile, garden


@receiver(user_logged_in)
def create_workspace_on_login(sender, request, user, **kwargs):
    ensure_user_workspace(user)
