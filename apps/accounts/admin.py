from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from apps.accounts.models import AgentProfile, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class AgentProfileInline(admin.StackedInline):
    model = AgentProfile
    can_delete = False
    extra = 0
    verbose_name_plural = "Agent profile"


class UserAdmin(BaseUserAdmin):
    inlines = [AgentProfileInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
