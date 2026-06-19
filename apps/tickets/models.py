from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.tickets.choices import (
    CLOSED_STATUSES,
    EventVerb,
    Priority,
    Status,
    TicketType,
)


class Category(models.Model):
    """One-level ticket category tree (e.g. Network > VPN)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        if self.parent_id:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Ticket(models.Model):
    """An incident or service request tracked through its lifecycle."""

    key = models.CharField(max_length=12, unique=True, blank=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ticket_type = models.CharField(
        max_length=20, choices=TicketType, default=TicketType.INCIDENT
    )
    status = models.CharField(max_length=20, choices=Status, default=Status.NEW)
    priority = models.CharField(
        max_length=20, choices=Priority, default=Priority.P3_NORMAL
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_tickets",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tickets",
    )
    team = models.ForeignKey(
        "accounts.Team",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
    )
    asset = models.ForeignKey(
        "assets.Asset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
    )
    sla_policy = models.ForeignKey(
        "sla.SlaPolicy",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
    )
    sla_due_at = models.DateTimeField(null=True, blank=True)
    sla_breached = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "priority"])]

    def __str__(self) -> str:
        return f"{self.key or 'NEW'} {self.title}"

    @property
    def is_open(self) -> bool:
        return self.status not in CLOSED_STATUSES

    def evaluate_sla(self, *, persist: bool = True) -> bool:
        """Recompute ``sla_breached`` from the due time and resolution state."""
        if self.sla_due_at is None:
            self.sla_breached = False
        else:
            endpoint = self.resolved_at or timezone.now()
            self.sla_breached = endpoint > self.sla_due_at
        if persist and self.pk:
            type(self).objects.filter(pk=self.pk).update(sla_breached=self.sla_breached)
        return self.sla_breached

    def save(self, *args, **kwargs):
        from apps.sla.models import SlaPolicy

        creating = self._state.adding
        if creating:
            if self.sla_policy is None:
                self.sla_policy = SlaPolicy.for_priority(self.priority)
            if self.sla_due_at is None and self.sla_policy is not None:
                self.sla_due_at = self.sla_policy.resolution_due_from(timezone.now())
        self.evaluate_sla(persist=False)
        super().save(*args, **kwargs)
        if not self.key:
            prefix = "INC" if self.ticket_type == TicketType.INCIDENT else "SR"
            new_key = f"{prefix}-{self.pk:04d}"
            type(self).objects.filter(pk=self.pk).update(key=new_key)
            self.key = new_key
        if creating:
            self.log_event(EventVerb.CREATED, actor=self.requester)

    # --- worklog / audit helpers -------------------------------------------

    def log_event(self, verb, *, actor=None, from_value="", to_value=""):
        return TicketEvent.objects.create(
            ticket=self,
            actor=actor,
            verb=verb,
            from_value=from_value or "",
            to_value=to_value or "",
        )

    # --- state transitions (each records an audit event) -------------------

    def assign_to(self, user, *, actor=None):
        self.assignee = user
        if self.status == Status.NEW:
            self.status = Status.ASSIGNED
        self.save()
        self.log_event(
            EventVerb.ASSIGNED,
            actor=actor,
            to_value=user.get_username() if user else "",
        )

    def change_status(self, new_status, *, actor=None):
        old = self.status
        if old == new_status:
            return
        self.status = new_status
        if new_status == Status.RESOLVED and self.resolved_at is None:
            self.resolved_at = timezone.now()
        if new_status == Status.CLOSED and self.closed_at is None:
            self.closed_at = timezone.now()
        self.save()
        self.log_event(
            EventVerb.STATUS_CHANGED, actor=actor, from_value=old, to_value=new_status
        )

    def mark_resolved(self, *, actor=None):
        self.status = Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save()
        self.log_event(EventVerb.RESOLVED, actor=actor)

    def mark_closed(self, *, actor=None):
        self.status = Status.CLOSED
        self.closed_at = timezone.now()
        if self.resolved_at is None:
            self.resolved_at = self.closed_at
        self.save()
        self.log_event(EventVerb.CLOSED, actor=actor)

    def reopen(self, *, actor=None):
        self.status = Status.IN_PROGRESS
        self.resolved_at = None
        self.closed_at = None
        self.save()
        self.log_event(EventVerb.REOPENED, actor=actor)


class Comment(models.Model):
    """A worklog entry on a ticket. Internal comments are agent-only."""

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="comments",
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment on {self.ticket.key} by {self.author_id}"


class TicketEvent(models.Model):
    """An immutable audit entry forming the ticket timeline."""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ticket_events",
    )
    verb = models.CharField(max_length=20, choices=EventVerb)
    from_value = models.CharField(max_length=100, blank=True)
    to_value = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.ticket.key}: {self.verb}"
