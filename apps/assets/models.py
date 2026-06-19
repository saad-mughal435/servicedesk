from django.conf import settings
from django.db import models


class Asset(models.Model):
    """A light CMDB entry: hardware or software a ticket can reference."""

    class AssetType(models.TextChoices):
        LAPTOP = "laptop", "Laptop"
        DESKTOP = "desktop", "Desktop"
        SERVER = "server", "Server"
        NETWORK = "network", "Network device"
        PRINTER = "printer", "Printer"
        MOBILE = "mobile", "Mobile device"
        SOFTWARE = "software", "Software"

    class Status(models.TextChoices):
        IN_USE = "in_use", "In use"
        IN_STOCK = "in_stock", "In stock"
        REPAIR = "repair", "In repair"
        RETIRED = "retired", "Retired"

    asset_tag = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    asset_type = models.CharField(
        max_length=20, choices=AssetType, default=AssetType.LAPTOP
    )
    status = models.CharField(max_length=20, choices=Status, default=Status.IN_USE)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assets",
    )
    location = models.CharField(max_length=120, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    purchased_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_tag"]

    def __str__(self) -> str:
        return f"{self.asset_tag} - {self.name}"
