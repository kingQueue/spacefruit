from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="spacefruit_profile")
    display_name = models.CharField(max_length=80, blank=True)
    location_label = models.CharField(max_length=120, blank=True)
    timezone = models.CharField(max_length=64, default="America/New_York")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.email or self.user.get_username()


class Garden(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        COMMUNITY = "community", "Community"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_gardens")
    name = models.CharField(max_length=100, default="My SpaceFruit Garden")
    visibility = models.CharField(max_length=12, choices=Visibility.choices, default=Visibility.PRIVATE)
    location_label = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class GardenMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

    garden = models.ForeignKey(Garden, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="garden_memberships")
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["garden", "user"], name="unique_garden_member")]


class GardenPlot(models.Model):
    class Status(models.TextChoices):
        EMPTY = "empty", "Empty"
        PLANTED = "planted", "Planted"
        HARVESTED = "harvested", "Harvested"

    garden = models.ForeignKey(Garden, on_delete=models.CASCADE, related_name="plots")
    label = models.CharField(max_length=24)
    plant_type = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.EMPTY)
    health_status = models.CharField(max_length=100, blank=True)
    health_issues = models.JSONField(default=list, blank=True)
    planted_at = models.DateTimeField(null=True, blank=True)
    last_monitored_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["garden", "label"], name="unique_plot_label_per_garden")]


class HarvestInventoryItem(models.Model):
    garden = models.ForeignKey(Garden, on_delete=models.CASCADE, related_name="harvest_inventory")
    plant_type = models.CharField(max_length=80)
    quantity = models.PositiveIntegerField(default=0)
    image_path = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["garden", "plant_type"], name="unique_harvest_type_per_garden")]


class MarketplaceListing(models.Model):
    class Section(models.TextChoices):
        TRADE = "trade", "Trade"
        BUY = "buy", "Buy / Sell"
        DONATE = "donate", "Donate"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marketplace_listings")
    garden = models.ForeignKey(Garden, on_delete=models.CASCADE, related_name="marketplace_listings")
    section = models.CharField(max_length=8, choices=Section.choices)
    plant_type = models.CharField(max_length=80)
    quantity = models.PositiveIntegerField()
    weight = models.DecimalField(max_digits=8, decimal_places=2)
    weight_unit = models.CharField(max_length=4, default="lb")
    asking_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    image_path = models.CharField(max_length=200, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["section", "active", "created_at"])]
