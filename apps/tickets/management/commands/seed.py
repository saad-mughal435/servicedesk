"""Seed realistic demo data for the service desk.

Idempotent: groups, users, teams, SLA policies, categories and assets are
created with ``get_or_create``; tickets are only generated on an empty database
unless ``--flush`` is passed (which clears tickets + assets first). A fixed RNG
seed keeps the generated data stable between runs.
"""

import random
from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import AgentProfile, Team
from apps.assets.models import Asset
from apps.sla.models import SlaPolicy
from apps.tickets.choices import Priority, Status, TicketType
from apps.tickets.models import Category, Comment, Ticket

PASSWORD = "demo12345"

SLA_DEFS = [
    ("Critical response", Priority.P1_CRITICAL, 30, 240, False),
    ("High priority", Priority.P2_HIGH, 60, 480, False),
    ("Standard", Priority.P3_NORMAL, 120, 1440, True),
    ("Low priority", Priority.P4_LOW, 240, 2880, False),
]

TEAM_DEFS = [
    ("Service Desk L1", "First-line triage and common requests."),
    ("Network Operations", "Connectivity, VPN, firewall and Wi-Fi."),
    ("Field Support", "On-site hardware and desk-side support."),
]

CATEGORY_DEFS = [
    ("Hardware", None),
    ("Laptop", "Hardware"),
    ("Printer", "Hardware"),
    ("Network", None),
    ("VPN", "Network"),
    ("Wi-Fi", "Network"),
    ("Access", None),
    ("Password reset", "Access"),
    ("Software", None),
    ("Email", "Software"),
]

TICKET_TITLES = [
    "Laptop won't power on after update",
    "VPN disconnects every few minutes",
    "Cannot access shared drive",
    "Outlook stuck on 'trying to connect'",
    "Request new starter laptop and accounts",
    "Printer on 3rd floor jams repeatedly",
    "Password reset for finance portal",
    "Wi-Fi very slow in the warehouse",
    "Request additional monitor",
    "Teams audio not working on headset",
    "Blue screen on startup",
    "Phishing email reported by user",
    "MFA device lost - needs re-enrolment",
    "Software install request: AutoCAD",
    "Disk almost full on workstation",
    "Email bouncing to external domain",
    "Badge access not working at side door",
    "Server backup job failed overnight",
    "Slow performance on ERP module",
    "New hire onboarding - IT setup",
    "Keyboard keys sticking",
    "Cannot print to network printer",
    "Account locked after travel",
    "Request file restore from backup",
]

DESCRIPTIONS = [
    "User reports the issue started this morning. No recent changes on their side.",
    "Reproduced on a second device. Escalating for investigation.",
    "Affects a single user; workaround applied while we investigate root cause.",
    "Recurring problem - third report this month from the same area.",
    "Submitted via the portal. Awaiting hardware availability.",
    "Logged from a phone call; details confirmed with the requester.",
]

ASSET_DEFS = [
    ("laptop", "LAP", "ThinkPad T14", ["Head office", "Warehouse", "Remote"]),
    ("desktop", "DSK", "OptiPlex 7010", ["Head office", "Finance", "Reception"]),
    ("server", "SRV", "PowerEdge R650", ["DC Rack A", "DC Rack B"]),
    ("network", "NET", "Catalyst 9200 switch", ["DC Rack A", "Floor 2 IDF"]),
    ("printer", "PRN", "HP LaserJet M507", ["Floor 1", "Floor 3"]),
    ("mobile", "MOB", "iPhone 15", ["Sales", "Field"]),
]


class Command(BaseCommand):
    help = "Seed demo data for the service desk."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing tickets and assets before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(1234)
        now = timezone.now()

        if options["flush"]:
            Ticket.objects.all().delete()
            Asset.objects.all().delete()
            self.stdout.write("Flushed existing tickets and assets.")

        groups = self._seed_groups()
        users = self._seed_users(groups)
        teams = self._seed_teams(users)
        self._seed_sla()
        categories = self._seed_categories()

        requesters = [u for u in users if u.groups.filter(name="requesters").exists()]
        agents = [u for u in users if u.groups.filter(name="agents").exists()]

        assets = self._seed_assets(users)

        if Ticket.objects.exists() and not options["flush"]:
            self.stdout.write(
                "Tickets already present; pass --flush to regenerate. "
                "Skipping ticket creation."
            )
        else:
            self._seed_tickets(now, requesters, agents, teams, categories, assets)

        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete: "
                f"{User.objects.count()} users, "
                f"{Team.objects.count()} teams, "
                f"{Asset.objects.count()} assets, "
                f"{Ticket.objects.count()} tickets "
                f"({Ticket.objects.filter(sla_breached=True).count()} SLA-breached). "
                "Demo logins: manager / agent / requester (password 'demo12345')."
            )
        )

    # -- seed steps ---------------------------------------------------------

    def _seed_groups(self):
        groups = {}
        for name in ("agents", "managers", "requesters"):
            groups[name], _ = Group.objects.get_or_create(name=name)

        # Managers: full control of the domain apps.
        manager_perms = Permission.objects.filter(
            content_type__app_label__in=["tickets", "accounts", "assets", "sla"]
        )
        groups["managers"].permissions.set(manager_perms)

        # Agents: work tickets (no delete), read reference data.
        agent_perms = list(
            Permission.objects.filter(content_type__app_label="tickets").exclude(
                codename__startswith="delete"
            )
        )
        agent_perms += list(
            Permission.objects.filter(
                content_type__app_label__in=["assets", "sla", "accounts"],
                codename__startswith="view",
            )
        )
        groups["agents"].permissions.set(agent_perms)

        # Requesters: no admin permissions.
        groups["requesters"].permissions.clear()
        return groups

    def _seed_users(self, groups):
        specs = [
            ("manager", "managers", True),
            ("agent", "agents", True),
            ("agent2", "agents", True),
            ("agent3", "agents", True),
            ("requester", "requesters", False),
            ("nadia", "requesters", False),
            ("omar", "requesters", False),
            ("li.wei", "requesters", False),
        ]
        users = []
        for username, group_name, is_staff in specs:
            user, _ = User.objects.get_or_create(username=username)
            user.email = f"{username}@example.com"
            user.is_staff = is_staff
            user.set_password(PASSWORD)
            user.save()
            user.groups.set([groups[group_name]])
            users.append(user)
        return users

    def _seed_teams(self, users):
        teams = []
        agents = [u for u in users if u.groups.filter(name="agents").exists()]
        for i, (name, desc) in enumerate(TEAM_DEFS):
            team, _ = Team.objects.get_or_create(
                slug=slugify(name), defaults={"name": name, "description": desc}
            )
            teams.append(team)
            if i < len(agents):
                AgentProfile.objects.update_or_create(
                    user=agents[i],
                    defaults={"team": team, "title": "Support engineer"},
                )
        return teams

    def _seed_sla(self):
        for name, priority, response, resolution, is_default in SLA_DEFS:
            SlaPolicy.objects.get_or_create(
                priority=priority,
                defaults={
                    "name": name,
                    "response_minutes": response,
                    "resolution_minutes": resolution,
                    "is_default": is_default,
                },
            )

    def _seed_categories(self):
        created = {}
        for name, parent_name in CATEGORY_DEFS:
            parent = created.get(parent_name) if parent_name else None
            cat, _ = Category.objects.get_or_create(
                slug=slugify(f"{parent_name}-{name}" if parent_name else name),
                defaults={"name": name, "parent": parent},
            )
            created[name] = cat
        return list(created.values())

    def _seed_assets(self, users):
        assets = []
        for asset_type, prefix, model_name, locations in ASSET_DEFS:
            for n in range(1, 8):
                tag = f"{prefix}-{n:04d}"
                asset, _ = Asset.objects.get_or_create(
                    asset_tag=tag,
                    defaults={
                        "name": model_name,
                        "asset_type": asset_type,
                        "location": random.choice(locations),
                        "assigned_to": random.choice(users),
                        "serial_number": f"SN{random.randint(100000, 999999)}",
                    },
                )
                assets.append(asset)
        return assets

    def _seed_tickets(self, now, requesters, agents, teams, categories, assets):
        status_pool = (
            [Status.NEW] * 3
            + [Status.ASSIGNED] * 3
            + [Status.IN_PROGRESS] * 4
            + [Status.ON_HOLD] * 2
            + [Status.RESOLVED] * 4
            + [Status.CLOSED] * 3
        )
        priority_pool = (
            [Priority.P1_CRITICAL] * 2
            + [Priority.P2_HIGH] * 4
            + [Priority.P3_NORMAL] * 7
            + [Priority.P4_LOW] * 3
        )

        for _ in range(60):
            status = random.choice(status_pool)
            priority = random.choice(priority_pool)
            ttype = random.choice(
                [TicketType.INCIDENT, TicketType.INCIDENT, TicketType.SERVICE_REQUEST]
            )
            assignee = None
            team = None
            if status != Status.NEW:
                assignee = random.choice(agents)
                team = random.choice(teams)

            ticket = Ticket(
                title=random.choice(TICKET_TITLES),
                description=random.choice(DESCRIPTIONS),
                ticket_type=ttype,
                priority=priority,
                status=status,
                category=random.choice(categories),
                requester=random.choice(requesters),
                assignee=assignee,
                team=team,
                asset=random.choice(assets) if random.random() < 0.5 else None,
            )
            ticket.save()  # sets key + SLA, logs the 'created' event

            # Backdate created_at/SLA so ages and breaches look realistic.
            # ~22% of tickets are made to breach; the rest stay within SLA.
            policy = ticket.sla_policy
            res = policy.resolution_minutes if policy else 1440
            should_breach = random.random() < 0.22

            if status in (Status.RESOLVED, Status.CLOSED):
                created = now - timedelta(minutes=random.randint(res // 2, res * 4))
                factor = random.uniform(1.1, 1.8) if should_breach else random.uniform(0.2, 0.85)
                resolved = min(created + timedelta(minutes=int(res * factor)), now)
                fields = {"created_at": created, "resolved_at": resolved}
                if status == Status.CLOSED:
                    fields["closed_at"] = min(resolved + timedelta(hours=6), now)
            else:
                factor = random.uniform(1.2, 3.0) if should_breach else random.uniform(0.05, 0.7)
                created = now - timedelta(minutes=int(res * factor))
                fields = {"created_at": created}
            if policy is not None:
                fields["sla_due_at"] = policy.resolution_due_from(created)

            Ticket.objects.filter(pk=ticket.pk).update(**fields)
            ticket.refresh_from_db()
            ticket.evaluate_sla(persist=True)

            for _ in range(random.randint(0, 3)):
                author = random.choice(agents + requesters)
                Comment.objects.create(
                    ticket=ticket,
                    author=author,
                    body=random.choice(DESCRIPTIONS),
                    is_internal=random.random() < 0.3
                    and author.groups.filter(name="agents").exists(),
                )
