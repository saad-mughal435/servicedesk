"""Refresh SLA breach flags, escalate newly-breached tickets, and notify.

Designed to run on a schedule (cron / Render Cron Job). Idempotent: a ticket is
only escalated and notified on the sweep where it first breaches, because the
breach flag is then set and subsequent sweeps skip it.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tickets.choices import CLOSED_STATUSES, EventVerb, Priority
from apps.tickets.models import Ticket, send_notification

# Priority order low → high, for one-level escalation on breach.
_LADDER = [Priority.P4_LOW, Priority.P3_NORMAL, Priority.P2_HIGH, Priority.P1_CRITICAL]
AT_RISK_THRESHOLD = 0.75  # fraction of the SLA window elapsed


class Command(BaseCommand):
    help = "Refresh SLA breach flags, escalate newly-breached tickets, and notify."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-escalate",
            action="store_true",
            help="Mark breaches and notify, but do not bump priority.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        open_qs = Ticket.objects.exclude(status__in=CLOSED_STATUSES).select_related("assignee")
        breached = at_risk = 0

        for ticket in open_qs:
            if ticket.sla_due_at is None or ticket.sla_breached:
                continue

            if ticket.sla_due_at < now:
                breached += 1
                fields = {"sla_breached": True}
                ticket.sla_breached = True

                old_priority = ticket.priority
                if not options["no_escalate"] and ticket.priority != Priority.P1_CRITICAL:
                    idx = _LADDER.index(ticket.priority) if ticket.priority in _LADDER else 1
                    ticket.priority = _LADDER[idx + 1].value
                    fields["priority"] = ticket.priority

                Ticket.objects.filter(pk=ticket.pk).update(**fields)
                if "priority" in fields:
                    ticket.log_event(
                        EventVerb.PRIORITY_CHANGED,
                        from_value=old_priority,
                        to_value=ticket.priority,
                    )
                send_notification(
                    ticket.assignee,
                    ticket,
                    f"SLA breached on {ticket.key}: {ticket.title}",
                    email=True,
                )
            else:
                window = (ticket.sla_due_at - ticket.created_at).total_seconds()
                used = (now - ticket.created_at).total_seconds()
                if window > 0 and used / window >= AT_RISK_THRESHOLD:
                    at_risk += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"SLA sweep: {breached} newly breached (escalated + notified), "
                f"{at_risk} at risk."
            )
        )
