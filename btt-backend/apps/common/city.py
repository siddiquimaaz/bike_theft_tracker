"""
apps/common/city.py
City-name normalisation and queryset scoping.

City is stored as free text, so every comparison has to be case- and
whitespace-insensitive on both sides.  Doing that inline invites drift between
call sites — a view that forgets Trim() silently stops matching " Karachi ".
"""
from django.db.models.functions import Lower, Trim


def normalize_city(city) -> str:
    """Lowercase and strip a city name for comparison. None becomes ''."""
    return (city or "").strip().lower()


def filter_by_city(qs, city, field_name="city"):
    """
    Scope `qs` to rows whose `field_name` matches `city`, ignoring case and
    surrounding whitespace.  An empty/None city matches nothing rather than
    everything — a user with no city configured must not see the whole table.
    """
    normalized_city = normalize_city(city)
    if not normalized_city:
        return qs.none()
    return qs.annotate(_city_norm=Lower(Trim(field_name))).filter(_city_norm=normalized_city)


def cities_match(left, right) -> bool:
    """True when two free-text city names refer to the same city."""
    left_norm = normalize_city(left)
    return bool(left_norm) and left_norm == normalize_city(right)
