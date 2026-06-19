import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def groups(db):
    return {
        name: Group.objects.create(name=name)
        for name in ("agents", "managers", "requesters")
    }


@pytest.fixture
def make_user(db, groups):
    def _make(username, group=None, **kwargs):
        user = User.objects.create_user(username=username, password="pw123456", **kwargs)
        if group:
            user.groups.add(groups[group])
        return user

    return _make


@pytest.fixture
def agent_user(make_user):
    return make_user("agent", "agents", is_staff=True)


@pytest.fixture
def manager_user(make_user):
    return make_user("manager", "managers", is_staff=True)


@pytest.fixture
def requester_user(make_user):
    return make_user("requester", "requesters")
