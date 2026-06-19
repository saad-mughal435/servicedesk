"""Role-based permissions, keyed off Django Groups.

Roles: ``requesters`` (raise + track their own tickets), ``agents`` (work all
tickets), ``managers`` (agents + reassign + delete + edit config). Superusers
pass every check.
"""

from django.conf import settings
from rest_framework import permissions

AGENTS = "agents"
MANAGERS = "managers"


def in_group(user, name: str) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.groups.filter(name=name).exists())
    )


def is_agent(user) -> bool:
    return in_group(user, AGENTS) or in_group(user, MANAGERS)


def is_manager(user) -> bool:
    return in_group(user, MANAGERS)


class IsAgent(permissions.BasePermission):
    message = "This action requires an agent account."

    def has_permission(self, request, view):
        return is_agent(request.user)


class IsManager(permissions.BasePermission):
    message = "This action requires a manager account."

    def has_permission(self, request, view):
        return is_manager(request.user)


class ReadOnlyOrManager(permissions.BasePermission):
    """Read for any authenticated user; writes restricted to managers."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return is_manager(request.user)


class DemoModeDeleteGuard(permissions.BasePermission):
    """In DEMO_MODE, block deletes for everyone except a real superuser."""

    message = "Deleting records is disabled in the public demo."

    def has_permission(self, request, view):
        if (
            settings.DEMO_MODE
            and request.method == "DELETE"
            and not (request.user and request.user.is_superuser)
        ):
            return False
        return True
