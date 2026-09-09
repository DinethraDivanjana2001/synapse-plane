"""Deterministic extraction of the few things an LLM shouldn't be trusted to
compute reliably: which calendar date "today"/"tomorrow" means, and which
meal's hours apply. Kept out of the LLM prompt entirely — date arithmetic and
keyword matching are exact operations, not judgment calls (see CLAUDE.md:
"state transitions are deterministic")."""

import re
from datetime import datetime, timedelta, timezone

_DEMO_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

MEAL_HOURS: dict[str, tuple[int, ...]] = {
    "breakfast": (7, 8, 9),
    "lunch": (12, 13, 14),
    "dinner": (17, 18, 19, 20, 21),
}


def resolve_date(intent: str, now: datetime | None = None) -> str:
    """ "today"/"tonight" -> now; "tomorrow" -> now+1; a weekday name -> the
    next occurrence of that weekday; anything else -> now (a reasonable
    default for "find me a restaurant", which implies "now")."""
    now = now or datetime.now(_DEMO_TIMEZONE)
    text = intent.lower()

    if "tomorrow" in text:
        return (now + timedelta(days=1)).date().isoformat()

    for i, day_name in enumerate(_WEEKDAYS):
        if re.search(rf"\b{day_name}\b", text):
            days_ahead = (i - now.weekday()) % 7
            days_ahead = days_ahead or 7  # "monday" on a Monday means next Monday
            return (now + timedelta(days=days_ahead)).date().isoformat()

    return now.date().isoformat()


def resolve_meal(intent: str) -> str:
    text = intent.lower()
    if "breakfast" in text:
        return "breakfast"
    if "lunch" in text:
        return "lunch"
    return "dinner"  # the system's primary supported use case
