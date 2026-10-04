from app.core.config import Settings, get_settings
from app.services.restaurants.base import RestaurantProvider
from app.services.restaurants.geoapify import GeoapifyRestaurantProvider
from app.services.restaurants.mock import MockRestaurantProvider


def get_restaurant_provider(settings: Settings | None = None) -> RestaurantProvider:
    settings = settings or get_settings()
    if settings.geoapify_api_key.strip():
        return GeoapifyRestaurantProvider(api_key=settings.geoapify_api_key.strip())
    return MockRestaurantProvider()
