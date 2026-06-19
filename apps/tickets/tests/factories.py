import factory
from django.contrib.auth.models import User

from apps.tickets.models import Category, Ticket


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ticket

    title = factory.Sequence(lambda n: f"Ticket {n}")
    description = "Generated for tests."
    requester = factory.SubFactory(UserFactory)
