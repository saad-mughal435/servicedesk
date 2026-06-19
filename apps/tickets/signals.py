from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.tickets.choices import EventVerb
from apps.tickets.models import Comment, TicketEvent


@receiver(post_save, sender=Comment)
def log_comment_event(sender, instance, created, **kwargs):
    """Record a 'commented' event so the audit timeline stays automatic."""
    if created:
        TicketEvent.objects.create(
            ticket=instance.ticket,
            actor=instance.author,
            verb=EventVerb.COMMENTED,
        )
