"""AI triage & assist for tickets.

Live mode calls the Anthropic API with a server-side key; when no key is
configured (or a call fails) it falls back to a deterministic mock so the demo
always works and CI needs no secret. Every result carries ``source`` =
``"ai"`` or ``"mock"`` so the UI can label it honestly.
"""

import json

from django.conf import settings

from apps.tickets.choices import Priority

# Keyword rules for the mock triage path: (keywords, category name, priority).
_TRIAGE_RULES = [
    (("server", "outage", "down", "backup", "production"), "Network", Priority.P1_CRITICAL),
    (("vpn", "network", "wifi", "wi-fi", "connect", "firewall"), "Network", Priority.P2_HIGH),
    (("password", "login", "locked", "mfa", "access", "account"), "Access", Priority.P2_HIGH),
    (("laptop", "power", "boot", "screen", "keyboard"), "Hardware", Priority.P3_NORMAL),
    (("printer", "print", "scanner"), "Printer", Priority.P4_LOW),
    (("outlook", "email", "mailbox", "smtp"), "Email", Priority.P3_NORMAL),
    (("install", "software", "license", "application"), "Software", Priority.P3_NORMAL),
]


def ai_available() -> bool:
    """True when a live Anthropic key is configured."""
    return bool(getattr(settings, "ANTHROPIC_API_KEY", ""))


def _client():
    import anthropic

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _ticket_context(ticket) -> str:
    lines = [
        f"Key: {ticket.key}",
        f"Title: {ticket.title}",
        f"Type: {ticket.get_ticket_type_display()}",
        f"Priority: {ticket.get_priority_display()}",
        f"Status: {ticket.get_status_display()}",
        f"Description: {ticket.description or '(none)'}",
        "Comments:",
    ]
    for c in ticket.comments.all()[:20]:
        who = c.author.username if c.author_id else "system"
        lines.append(f"  - {who}: {c.body}")
    return "\n".join(lines)


# --- public API --------------------------------------------------------------


def suggest_triage(title: str, description: str = "") -> dict:
    """Suggest a category + priority for a ticket from its title/description."""
    if ai_available():
        try:
            return _ai_triage(title, description)
        except Exception:
            pass  # fall through to the mock
    text = f"{title} {description}".lower()
    for keywords, category, priority in _TRIAGE_RULES:
        hits = [k for k in keywords if k in text]
        if hits:
            return {
                "category": category,
                "priority": priority.value,
                "reasoning": f"Matched keywords: {', '.join(hits)}.",
                "source": "mock",
            }
    return {
        "category": "Software",
        "priority": Priority.P3_NORMAL.value,
        "reasoning": "No strong signal; defaulted to a normal software request.",
        "source": "mock",
    }


def summarize_ticket(ticket) -> dict:
    if ai_available():
        try:
            return {"text": _ai_summarize(ticket), "source": "ai"}
        except Exception:
            pass
    n = ticket.comments.count()
    return {
        "text": (
            f"{ticket.key} — {ticket.title}. Currently {ticket.get_status_display()} "
            f"at {ticket.get_priority_display()} with {n} comment(s)."
        ),
        "source": "mock",
    }


def draft_reply(ticket) -> dict:
    if ai_available():
        try:
            return {"text": _ai_draft(ticket), "source": "ai"}
        except Exception:
            pass
    requester = ticket.requester.username
    return {
        "text": (
            f"Hi {requester},\n\nThanks for raising \"{ticket.title}\". We're looking "
            f"into it and will update you shortly. If anything changes on your side, "
            f"reply here.\n\nRegards,\nIT Service Desk"
        ),
        "source": "mock",
    }


# --- live (Anthropic) paths ---------------------------------------------------


def _ai_triage(title: str, description: str) -> dict:
    from apps.tickets.models import Category

    categories = list(Category.objects.filter(is_active=True).values_list("name", flat=True))
    schema = {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": categories or ["Software"]},
            "priority": {"type": "string", "enum": [p.value for p in Priority]},
            "reasoning": {"type": "string"},
        },
        "required": ["category", "priority", "reasoning"],
        "additionalProperties": False,
    }
    resp = _client().messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=400,
        system=(
            "You are an IT service-desk triage assistant. Classify the ticket into "
            "one of the provided categories and assign a priority "
            "(p1_critical highest, p4_low lowest). Be concise."
        ),
        messages=[
            {"role": "user", "content": f"Title: {title}\n\nDescription: {description}"}
        ],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    data = json.loads(text)
    data["source"] = "ai"
    return data


def _ai_summarize(ticket) -> str:
    resp = _client().messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=300,
        system="Summarize this IT support ticket in 2-3 sentences for an agent picking it up.",
        messages=[{"role": "user", "content": _ticket_context(ticket)}],
    )
    return next((b.text for b in resp.content if b.type == "text"), "").strip()


def _ai_draft(ticket) -> str:
    resp = _client().messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=400,
        system=(
            "Draft a brief, professional reply from the IT service desk to the "
            "ticket requester. Acknowledge the issue and give a clear next step."
        ),
        messages=[{"role": "user", "content": _ticket_context(ticket)}],
    )
    return next((b.text for b in resp.content if b.type == "text"), "").strip()
