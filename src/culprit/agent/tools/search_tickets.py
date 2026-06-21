"""Mocked retrieval tool: search a fixed corpus of resolved prior tickets.

Deterministic and side-effect-free. When ``product_area`` is provided the search
is scoped to that area (the correct behavior). When it is omitted the search
falls back to an *unfiltered* top-k over the whole corpus — which is exactly the
silent-failure seed in the README: no filter -> mixed, irrelevant context ->
the planner routes the ticket to the wrong team.
"""

from __future__ import annotations

from typing import Any

CAPABILITIES = frozenset({"search"})

# Resolved prior tickets, labeled with the team/priority they were handled by.
# Several per product area so majority-vote routing in the planner is stable.
CORPUS: list[dict[str, Any]] = [
    {"id": "T-1001", "title": "VPN disconnects every few minutes",
     "product_area": "networking", "team": "Network Engineering", "priority": "High"},
    {"id": "T-1002", "title": "Cannot reach internal sites over VPN",
     "product_area": "networking", "team": "Network Engineering", "priority": "High"},
    {"id": "T-1003", "title": "Wifi drops in the east building",
     "product_area": "networking", "team": "Network Engineering", "priority": "Medium"},
    {"id": "T-2001", "title": "Office printer jams on duplex",
     "product_area": "printing", "team": "IT Hardware Support", "priority": "Low"},
    {"id": "T-2002", "title": "Printer not found on the network",
     "product_area": "printing", "team": "IT Hardware Support", "priority": "Medium"},
    {"id": "T-3001", "title": "Cannot send external email",
     "product_area": "email", "team": "Messaging & Collaboration", "priority": "High"},
    {"id": "T-3002", "title": "Calendar invites not syncing",
     "product_area": "email", "team": "Messaging & Collaboration", "priority": "Medium"},
    {"id": "T-4001", "title": "Locked out of my account",
     "product_area": "identity", "team": "Identity & Access Management", "priority": "High"},
    {"id": "T-4002", "title": "MFA device lost, need reset",
     "product_area": "identity", "team": "Identity & Access Management", "priority": "Medium"},
    {"id": "T-5001", "title": "CRM app throws 500 on save",
     "product_area": "software", "team": "Application Support", "priority": "High"},
    {"id": "T-5002", "title": "Report export button does nothing",
     "product_area": "software", "team": "Application Support", "priority": "Low"},
]


def _score(corpus_ticket: dict[str, Any], query: str) -> float:
    """Cheap lexical overlap score between a query and a corpus ticket title."""
    if not query:
        return 0.5
    q = {w for w in query.lower().split() if len(w) > 2}
    if not q:
        return 0.5
    title = {w for w in corpus_ticket["title"].lower().split() if len(w) > 2}
    overlap = len(q & title)
    return round(min(1.0, 0.5 + 0.1 * overlap), 3)


def search_tickets(
    product_area: str | None = None,
    query: str = "",
    limit: int = 3,
) -> dict[str, Any]:
    """Return resolved prior tickets relevant to the request.

    Scoped to ``product_area`` when given; otherwise an unfiltered top-k (the
    degraded path). Always returns ``status == "ok"`` — a wrong filter is a
    *silent* fault, not an error, which is the whole point.
    """
    if limit < 1:
        return {"status": "error", "reason": "limit must be >= 1"}
    if product_area:
        pool = [t for t in CORPUS if t["product_area"] == product_area.lower()]
        filtered = True
    else:
        pool = list(CORPUS)
        filtered = False

    ranked = sorted(pool, key=lambda t: _score(t, query), reverse=True)
    results = [{**t, "score": _score(t, query)} for t in ranked[:limit]]
    return {
        "status": "ok",
        "filtered": filtered,
        "product_area": product_area,
        "count": len(results),
        "results": results,
    }
