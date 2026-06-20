"""Vendor-aware ticket search.

On PostgreSQL this uses real full-text search (``to_tsvector`` / ``to_tsquery``
via Django's SearchVector/SearchQuery) ranked by relevance. On SQLite (local
dev / CI) it falls back to a case-insensitive substring match so the same code
path works everywhere.
"""

from django.db import connection
from django.db.models import Q


def search_tickets(qs, query):
    query = (query or "").strip()
    if not query:
        return qs

    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import (
            SearchQuery,
            SearchRank,
            SearchVector,
        )

        vector = SearchVector("title", "description", config="english")
        search_query = SearchQuery(query, config="english")
        return (
            qs.annotate(rank=SearchRank(vector, search_query))
            .filter(Q(rank__gt=0) | Q(key__icontains=query))
            .order_by("-rank", "-created_at")
        )

    return qs.filter(
        Q(key__icontains=query)
        | Q(title__icontains=query)
        | Q(description__icontains=query)
    )
