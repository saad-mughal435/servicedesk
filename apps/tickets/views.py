"""Server-rendered service-desk pages (login-gated)."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.tickets.choices import CLOSED_STATUSES, Priority, Status
from apps.tickets.forms import CommentForm, TicketForm
from apps.tickets.metrics import compute_metrics
from apps.tickets.models import Ticket
from apps.tickets.permissions import is_agent

HIGH_PRIORITIES = [Priority.P1_CRITICAL, Priority.P2_HIGH]


def visible_tickets(user):
    """Agents/managers/staff see all tickets; requesters see only their own."""
    qs = Ticket.objects.select_related("assignee", "team", "category", "requester")
    if is_agent(user) or user.is_staff:
        return qs
    return qs.filter(requester=user)


@login_required
def dashboard(request):
    qs = visible_tickets(request.user)
    open_qs = qs.exclude(status__in=CLOSED_STATUSES)
    now = timezone.now()
    status_counts = {
        row["status"]: row["n"]
        for row in open_qs.values("status").annotate(n=Count("id"))
    }
    by_status = [
        (label, status_counts.get(value, 0)) for value, label in Status.choices
    ]
    context = {
        "total_open": open_qs.count(),
        "by_status": by_status,
        "high_priority": open_qs.filter(priority__in=HIGH_PRIORITIES).count(),
        "breached": open_qs.filter(sla_due_at__lt=now).count(),
        "my_open": qs.filter(assignee=request.user)
        .exclude(status__in=CLOSED_STATUSES)
        .order_by("priority", "sla_due_at")[:10],
        "recent": qs.order_by("-created_at")[:8],
        "is_agent": is_agent(request.user),
    }
    return render(request, "tickets/dashboard.html", context)


@login_required
def ticket_list(request):
    qs = visible_tickets(request.user)
    status_f = request.GET.get("status") or ""
    priority_f = request.GET.get("priority") or ""
    if status_f:
        qs = qs.filter(status=status_f)
    if priority_f:
        qs = qs.filter(priority=priority_f)
    context = {
        "tickets": qs.order_by("-created_at")[:200],
        "statuses": Status.choices,
        "priorities": Priority.choices,
        "status_f": status_f,
        "priority_f": priority_f,
    }
    return render(request, "tickets/ticket_list.html", context)


@login_required
def ticket_detail(request, key):
    ticket = get_object_or_404(visible_tickets(request.user), key=key)
    user_is_agent = is_agent(request.user)

    if request.method == "POST":
        intent = request.POST.get("action")
        if intent == "comment":
            form = CommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.ticket = ticket
                comment.author = request.user
                if not user_is_agent:
                    comment.is_internal = False
                comment.save()
                return redirect("ticket-detail", key=ticket.key)
        elif user_is_agent and intent == "assign_me":
            ticket.assign_to(request.user, actor=request.user)
            return redirect("ticket-detail", key=ticket.key)
        elif user_is_agent and intent == "resolve":
            ticket.mark_resolved(actor=request.user)
            return redirect("ticket-detail", key=ticket.key)
        elif user_is_agent and intent == "reopen":
            ticket.reopen(actor=request.user)
            return redirect("ticket-detail", key=ticket.key)
    else:
        form = CommentForm()

    comments = ticket.comments.select_related("author")
    if not user_is_agent:
        comments = comments.filter(is_internal=False)
    context = {
        "ticket": ticket,
        "form": form,
        "comments": comments,
        "events": ticket.events.select_related("actor"),
        "is_agent": user_is_agent,
    }
    return render(request, "tickets/ticket_detail.html", context)


@login_required
def reports(request):
    if not is_agent(request.user):
        return redirect("dashboard")
    return render(request, "tickets/reports.html", {"metrics": compute_metrics()})


@login_required
def ticket_create(request):
    if request.method == "POST":
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.requester = request.user
            ticket.save()
            return redirect("ticket-detail", key=ticket.key)
    else:
        form = TicketForm()
    return render(request, "tickets/ticket_form.html", {"form": form})
