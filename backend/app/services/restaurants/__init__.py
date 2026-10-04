"""Restaurant search. Geoapify when configured, otherwise curated mock places."""

from app.services.restaurants.base import RestaurantProvider
from app.services.restaurants.factory import get_restaurant_provider
from app.services.restaurants.geoapify import GeoapifyRestaurantProvider, normalize_geoapify_feature
from app.services.restaurants.mock import MockRestaurantProvider

__all__ = [
    "GeoapifyRestaurantProvider",
    "MockRestaurantProvider",
    "RestaurantProvider",
    "get_restaurant_provider",
    "normalize_geoapify_feature",
]
