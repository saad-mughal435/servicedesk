"""DRF serializers and viewsets for the tickets domain."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tickets.models import Category, Comment, Ticket, TicketEvent
from apps.tickets.permissions import (
    DemoModeDeleteGuard,
    IsAgent,
    IsManager,
    is_agent,
)

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "is_active"]


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author_name", "body", "is_internal", "created_at"]
        read_only_fields = ["id", "author_name", "created_at"]


class TicketEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)
    verb_display = serializers.CharField(source="get_verb_display", read_only=True)

    class Meta:
        model = TicketEvent
        fields = [
            "id",
            "verb",
            "verb_display",
            "actor_name",
            "from_value",
            "to_value",
            "created_at",
        ]


class TicketListSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source="assignee.username", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "key",
            "title",
            "ticket_type",
            "status",
            "priority",
            "assignee_name",
            "team_name",
            "sla_due_at",
            "sla_breached",
            "created_at",
        ]


class TicketDetailSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source="requester.username", read_only=True)
    assignee_name = serializers.CharField(source="assignee.username", read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    events = TicketEventSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "key",
            "title",
            "description",
            "ticket_type",
            "status",
            "priority",
            "category",
            "requester_name",
            "assignee",
            "assignee_name",
            "team",
            "asset",
            "sla_policy",
            "sla_due_at",
            "sla_breached",
            "created_at",
            "updated_at",
            "resolved_at",
            "closed_at",
            "comments",
            "events",
        ]
        read_only_fields = [
            "id",
            "key",
            "requester_name",
            "sla_policy",
            "sla_due_at",
            "sla_breached",
            "created_at",
            "updated_at",
            "resolved_at",
            "closed_at",
        ]


class TicketViewSet(viewsets.ModelViewSet):
    """CRUD + lifecycle actions for tickets.

    Requesters see and create only their own tickets; agents and managers see
    everything. Deletes are manager-only (and disabled in demo mode).
    """

    queryset = Ticket.objects.select_related(
        "requester", "assignee", "team", "category", "sla_policy", "asset"
    ).all()
    filterset_fields = [
        "status",
        "priority",
        "ticket_type",
        "assignee",
        "team",
        "category",
        "sla_breached",
    ]
    search_fields = ["key", "title", "description"]
    ordering_fields = ["created_at", "sla_due_at", "priority", "updated_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return TicketListSerializer
        return TicketDetailSerializer

    def get_permissions(self):
        perms = [IsAuthenticated, DemoModeDeleteGuard]
        if self.action in ("update", "partial_update", "assign", "resolve", "reopen"):
            perms.append(IsAgent)
        elif self.action == "destroy":
            perms.append(IsManager)
        return [p() for p in perms]

    def get_queryset(self):
        qs = super().get_queryset()
        if is_agent(self.request.user) or self.request.user.is_staff:
            return qs
        return qs.filter(requester=self.request.user)

    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        if request.method == "POST":
            serializer = CommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(ticket=ticket, author=request.user)
            return Response(
                CommentSerializer(comment).data, status=status.HTTP_201_CREATED
            )
        qs = ticket.comments.all()
        if not (is_agent(request.user) or request.user.is_staff):
            qs = qs.filter(is_internal=False)
        return Response(CommentSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        assignee_id = request.data.get("assignee")
        assignee = get_object_or_404(User, pk=assignee_id) if assignee_id else None
        ticket.assign_to(assignee, actor=request.user)
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        ticket = self.get_object()
        ticket.mark_resolved(actor=request.user)
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        ticket = self.get_object()
        ticket.reopen(actor=request.user)
        return Response(self.get_serializer(ticket).data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    pagination_class = None
