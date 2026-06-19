from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.sla.models import SlaPolicy
from apps.tickets.permissions import DemoModeDeleteGuard, ReadOnlyOrManager


class SlaPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaPolicy
        fields = [
            "id",
            "name",
            "priority",
            "response_minutes",
            "resolution_minutes",
            "is_active",
            "is_default",
        ]


class SlaPolicyViewSet(viewsets.ModelViewSet):
    """Read for any authenticated user; writes are manager-only."""

    queryset = SlaPolicy.objects.all()
    serializer_class = SlaPolicySerializer
    permission_classes = [IsAuthenticated, ReadOnlyOrManager, DemoModeDeleteGuard]
    pagination_class = None
