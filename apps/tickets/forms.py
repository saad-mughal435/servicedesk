from django import forms

from apps.tickets.models import Comment, Ticket


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body", "is_internal"]
        widgets = {
            "body": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Add a comment or worklog note..."}
            ),
        }


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "ticket_type", "priority", "category", "asset"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }
