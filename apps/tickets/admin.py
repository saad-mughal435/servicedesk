from django.contrib import admin

from apps.tickets.choices import EventVerb, Priority, Status
from apps.tickets.models import Category, Comment, Notification, Ticket, TicketEvent

admin.site.site_header = "Service Desk administration"
admin.site.site_title = "Service Desk"
admin.site.index_title = "Operations"

# Priority order, low to high, for the escalate action.
_PRIORITY_LADDER = [
    Priority.P4_LOW,
    Priority.P3_NORMAL,
    Priority.P2_HIGH,
    Priority.P1_CRITICAL,
]


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("author", "body", "is_internal", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)


class TicketEventInline(admin.TabularInline):
    model = TicketEvent
    extra = 0
    fields = ("verb", "actor", "from_value", "to_value", "created_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "title",
        "ticket_type",
        "status",
        "priority",
        "assignee",
        "team",
        "sla_due_at",
        "sla_breached",
    )
    list_filter = ("status", "priority", "ticket_type", "team", "category")
    search_fields = (
        "key",
        "title",
        "description",
        "requester__username",
        "assignee__username",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = (
        "requester",
        "assignee",
        "asset",
        "category",
        "team",
        "sla_policy",
    )
    readonly_fields = (
        "key",
        "created_at",
        "updated_at",
        "resolved_at",
        "closed_at",
        "sla_due_at",
        "sla_breached",
    )
    inlines = [CommentInline, TicketEventInline]
    actions = ["assign_to_me", "resolve", "set_in_progress", "escalate_priority"]

    @admin.action(description="Assign selected tickets to me")
    def assign_to_me(self, request, queryset):
        for ticket in queryset:
            ticket.assign_to(request.user, actor=request.user)
        self.message_user(request, f"{queryset.count()} ticket(s) assigned to you.")

    @admin.action(description="Mark resolved")
    def resolve(self, request, queryset):
        count = 0
        for ticket in queryset:
            ticket.mark_resolved(actor=request.user)
            count += 1
        self.message_user(request, f"{count} ticket(s) resolved.")

    @admin.action(description="Mark in progress")
    def set_in_progress(self, request, queryset):
        for ticket in queryset:
            ticket.change_status(Status.IN_PROGRESS, actor=request.user)
        self.message_user(request, "Updated selected tickets.")

    @admin.action(description="Escalate priority one level")
    def escalate_priority(self, request, queryset):
        for ticket in queryset:
            idx = (
                _PRIORITY_LADDER.index(ticket.priority)
                if ticket.priority in _PRIORITY_LADDER
                else 1
            )
            if idx < len(_PRIORITY_LADDER) - 1:
                old = ticket.priority
                ticket.priority = _PRIORITY_LADDER[idx + 1]
                ticket.save()
                ticket.log_event(
                    EventVerb.PRIORITY_CHANGED,
                    actor=request.user,
                    from_value=old,
                    to_value=ticket.priority,
                )
        self.message_user(request, "Escalated selected tickets.")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)
    search_fields = ("ticket__key", "body")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("ticket", "author")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "text", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("user__username", "text")


@admin.register(TicketEvent)
class TicketEventAdmin(admin.ModelAdmin):
    list_display = ("ticket", "verb", "actor", "created_at")
    list_filter = ("verb",)
    search_fields = ("ticket__key",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
