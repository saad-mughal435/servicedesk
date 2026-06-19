from django.contrib import admin

from apps.sla.models import SlaPolicy


@admin.register(SlaPolicy)
class SlaPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "priority",
        "response_minutes",
        "resolution_minutes",
        "is_active",
        "is_default",
    )
    list_filter = ("is_active", "is_default")
    search_fields = ("name",)
