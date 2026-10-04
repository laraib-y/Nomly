"""Normalize and deduplicate restaurant candidates.

Deduplication prefers a provider id, then a normalized name near the same point.
"Jin's Korean Restaurant" and "Jins Korean Restaurant" a short walk apart become one card.
"""

import math
import re
import unicodedata

from app.schemas.restaurant import RestaurantCandidate

NAME_DISTANCE_METERS = 180


def dedupe_restaurants(restaurants: list[RestaurantCandidate]) -> list[RestaurantCandidate]:
    kept: list[RestaurantCandidate] = []
    seen_ids: set[str] = set()
    for restaurant in restaurants:
        external_id = restaurant.external_id.strip().lower()
        if external_id in seen_ids:
            continue
        if any(_same_place(restaurant, existing) for existing in kept):
            continue
        seen_ids.add(external_id)
        kept.append(restaurant)
    return kept


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def valid_coordinate(latitude: float | None, longitude: float | None) -> tuple[float, float] | None:
    if latitude is None or longitude is None:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def _same_place(left: RestaurantCandidate, right: RestaurantCandidate) -> bool:
    if normalize_name(left.name) != normalize_name(right.name):
        return False
    left_point = valid_coordinate(left.latitude, left.longitude)
    right_point = valid_coordinate(right.latitude, right.longitude)
    if left_point is None or right_point is None:
        return True
    return distance_meters(*left_point, *right_point) <= NAME_DISTANCE_METERS
