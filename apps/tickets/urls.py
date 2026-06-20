from django.urls import path

from apps.tickets import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tickets/", views.ticket_list, name="ticket-list"),
    path("reports/", views.reports, name="reports"),
    path("tickets/new/", views.ticket_create, name="ticket-create"),
    path("tickets/<str:key>/", views.ticket_detail, name="ticket-detail"),
]
