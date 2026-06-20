from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.tickets.choices import EventVerb
from apps.tickets.models import Comment, TicketEvent, send_notification


@receiver(post_save, sender=Comment)
def on_comment_created(sender, instance, created, **kwargs):
    """Record a 'commented' event and notify the other party."""
    if not created:
        return
    ticket = instance.ticket
    author = instance.author
    TicketEvent.objects.create(ticket=ticket, actor=author, verb=EventVerb.COMMENTED)

    text = f"New comment on {ticket.key}: {ticket.title}"
    if ticket.assignee_id and ticket.assignee != author:
        send_notification(ticket.assignee, ticket, text)
    if ticket.requester != author and not instance.is_internal:
        send_notification(ticket.requester, ticket, text)
