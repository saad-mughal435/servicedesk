from datetime import datetime

from django.db import models

from apps.sla.services import resolution_due
from apps.tickets.choices import Priority


class SlaPolicy(models.Model):
    """Response/resolution targets for a given priority.

    One active policy per priority; an optional default covers anything
    unmatched.
    """

    name = models.CharField(max_length=100)
    priority = models.CharField(max_length=20, choices=Priority, unique=True)
    response_minutes = models.PositiveIntegerField()
    resolution_minutes = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["priority"]
        verbose_name = "SLA policy"
        verbose_name_plural = "SLA policies"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_priority_display()})"

    def resolution_due_from(self, start: datetime) -> datetime:
        return resolution_due(start, self.resolution_minutes)

    @classmethod
    def for_priority(cls, priority: str) -> "SlaPolicy | None":
        policy = cls.objects.filter(priority=priority, is_active=True).first()
        if policy is None:
            policy = cls.objects.filter(is_default=True, is_active=True).first()
        return policy
