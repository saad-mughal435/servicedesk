from django.conf import settings
from django.db import models


class Team(models.Model):
    """A support queue that tickets are routed to (e.g. Service Desk L1)."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AgentProfile(models.Model):
    """ITSM attributes attached to a built-in ``User`` (kept off the User model)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_profile",
    )
    team = models.ForeignKey(
        Team,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    title = models.CharField(max_length=100, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.user.get_username()} profile"
