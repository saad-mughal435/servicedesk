from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.assets.models import Asset
from apps.tickets.permissions import DemoModeDeleteGuard, ReadOnlyOrManager


class AssetSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(
        source="assigned_to.username", read_only=True
    )

    class Meta:
        model = Asset
        fields = [
            "id",
            "asset_tag",
            "name",
            "asset_type",
            "status",
            "assigned_to",
            "assigned_to_name",
            "location",
            "serial_number",
            "purchased_on",
            "notes",
            "created_at",
            "updated_at",
        ]


class AssetViewSet(viewsets.ModelViewSet):
    """Read for any authenticated user; writes are manager-only."""

    queryset = Asset.objects.select_related("assigned_to").all()
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated, ReadOnlyOrManager, DemoModeDeleteGuard]
    filterset_fields = ["asset_type", "status", "assigned_to"]
    search_fields = ["asset_tag", "name", "serial_number"]
    ordering_fields = ["asset_tag", "created_at"]
