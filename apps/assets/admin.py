from django.contrib import admin

from apps.assets.models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "name", "asset_type", "status", "assigned_to", "location")
    list_filter = ("asset_type", "status")
    search_fields = ("asset_tag", "name", "serial_number")
    autocomplete_fields = ("assigned_to",)
