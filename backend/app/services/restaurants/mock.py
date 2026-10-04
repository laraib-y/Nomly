from app.schemas.ai import DinnerIntent
from app.schemas.restaurant import RestaurantCandidate
from app.services.restaurants.base import RestaurantProvider
from app.services.restaurants.restaurant_normalizer import dedupe_restaurants
from app.services.restaurants.restaurant_ranker import (
    apply_hard_constraints,
    cuisine_matches,
    rank_candidates,
    select_diverse_deck,
)

TARGET_COUNT = 12

CITY_CENTERS = {
    "burnaby": (49.2488, -122.9805),
    "vancouver": (49.2827, -123.1207),
    "richmond": (49.1666, -123.1336),
}

def _place(
    external_id: str,
    name: str,
    cuisine: str,
    price: int,
    rating: float,
    street: str,
    city: str,
    description: str,
    categories: list[str] | None = None,
    vibe: str = "casual",
) -> dict:
    return {
        "external_id": external_id,
        "name": name,
        "cuisine": cuisine,
        "price": price,
        "rating": rating,
        "street": street,
        "city": city,
        "description": description,
        "categories": categories or [cuisine],
        "vibe": vibe,
    }


# Home city is where the place actually sits. A Burnaby search should not
# silently reuse a Vancouver list, and the reverse is also true.
_CATALOG: list[dict] = [
    _place("mock-kinjo-sushi", "Kinjo Sushi", "Japanese", 2, 4.6, "4500 Kingsway", "Burnaby", "Neighborhood sushi counter with a short menu and a casual room.", ["Japanese", "Sushi"]),
    _place("mock-maple-izakaya", "Maple Izakaya", "Japanese", 2, 4.5, "329 North Rd", "Burnaby", "Small plates, skewers, and a relaxed weeknight feel.", ["Japanese", "Izakaya"], "casual"),
    _place("mock-north-ramen", "North Ramen", "Japanese", 1, 4.4, "4188 Hastings St", "Burnaby", "Casual ramen shop with a short, cheap menu.", ["Japanese", "Ramen"]),
    _place("mock-sora-donburi", "Sora Donburi", "Japanese", 2, 4.3, "5055 Kingsway", "Burnaby", "Rice bowls and a quiet counter.", ["Japanese"]),
    _place("mock-hearth-sushi", "Hearth Sushi", "Japanese", 2, 4.2, "6108 Willingdon", "Burnaby", "Neighbourhood sushi with room for a group.", ["Japanese", "Sushi"]),
    _place("mock-lantern-ramen", "Lantern Ramen", "Japanese", 1, 4.5, "1601 Hastings St", "Burnaby", "Quick bowls and a casual room.", ["Japanese", "Ramen"]),
    _place("mock-kumo-izakaya", "Kumo Izakaya", "Japanese", 2, 4.1, "7888 6th St", "Burnaby", "Skewers and small plates for a low-key night.", ["Japanese", "Izakaya"]),
    _place("mock-yoru-omakase", "Yoru Omakase", "Japanese", 4, 4.9, "4501 Kingsway", "Burnaby", "An expensive counter with a long set menu.", ["Japanese"], "fancy"),
    _place("mock-han-river-bbq", "Han River BBQ", "Korean", 2, 4.7, "1880 Willingdon Ave", "Burnaby", "Tabletop grills, banchan, and plenty of space for a group.", ["Korean", "Barbecue"]),
    _place("mock-seoul-night", "Seoul Night Kitchen", "Korean", 2, 4.4, "4700 Kingsway", "Burnaby", "Late bowls, fried chicken, and a lively but unfussy dining room.", ["Korean"]),
    _place("mock-banchan-house", "Banchan House", "Korean", 1, 4.6, "3020 Boundary Rd", "Burnaby", "Home-style plates and a casual group table.", ["Korean"]),
    _place("mock-oak-grill", "Oak Grill Korean", "Korean", 2, 4.3, "5288 Kingsway", "Burnaby", "Grills and stews without the fuss.", ["Korean"]),
    _place("mock-midnight-tofu", "Midnight Tofu", "Korean", 2, 4.5, "4120 Hastings St", "Burnaby", "Soft tofu stews and a warm room.", ["Korean"]),
    _place("mock-garden-korean", "Garden Korean", "Korean", 2, 4.2, "6280 Kingsway", "Burnaby", "Vegetable-forward Korean plates in a casual room.", ["Korean", "Vegetarian"], "casual"),
    _place("mock-palace-korean", "Palace Korean", "Korean", 4, 4.9, "4701 Kingsway", "Burnaby", "A dressier Korean tasting menu.", ["Korean"], "fancy"),
    _place("mock-pasta-lane", "Pasta Lane", "Italian", 2, 4.3, "2500 Boundary Rd", "Burnaby", "Fresh pasta and a friendly noise level.", ["Italian"]),
    _place("mock-north-shore-tacos", "North Shore Tacos", "Mexican", 1, 4.4, "4125 Hastings St", "Burnaby", "Weekend-style tacos and a patio that works for a crowd.", ["Mexican"]),
    _place("mock-spice-route", "Spice Route", "Indian", 2, 4.6, "5901 Kingsway", "Burnaby", "Family-style curries and breads meant to be passed around.", ["Indian"]),
    _place("mock-burger-club", "Burnaby Burger Club", "Burgers", 1, 4.0, "1020 Austin Ave", "Burnaby", "Smash burgers when nobody wants to dress up.", ["Burgers"]),
    _place("mock-green-bowl", "Green Bowl", "Vegetarian", 2, 4.2, "4220 Hastings St", "Burnaby", "Vegetarian grain bowls and a calm room.", ["Vegetarian"]),
    _place("mock-cedar-noodle", "Cedar Noodle Bar", "Chinese", 1, 4.2, "1601 Burnaby Heights", "Burnaby", "Hand-pulled noodles and a quick, casual counter.", ["Chinese"]),
    _place("mock-basil-brick", "Basil & Brick", "Thai", 2, 4.5, "5055 Canada Way", "Burnaby", "Curries and a bright room.", ["Thai"]),
    _place("mock-false-creek-pasta", "False Creek Pasta", "Italian", 2, 4.6, "88 W Pender St", "Vancouver", "Fresh pasta in downtown Vancouver.", ["Italian"]),
    _place("mock-coal-harbour-sushi", "Coal Harbour Sushi", "Japanese", 3, 4.7, "1055 W Hastings St", "Vancouver", "A brighter sushi room by the water.", ["Japanese", "Sushi"]),
    _place("mock-robson-izakaya", "Robson Izakaya", "Japanese", 2, 4.4, "850 Robson St", "Vancouver", "Skewers and a casual downtown room.", ["Japanese"]),
    _place("mock-main-street-tacos", "Main Street Tacos", "Mexican", 1, 4.5, "2280 Main St", "Vancouver", "Casual tacos on Main Street.", ["Mexican"]),
    _place("mock-commercial-korean", "Commercial Korean", "Korean", 2, 4.5, "1400 Commercial Dr", "Vancouver", "Grills and stews on Commercial Drive.", ["Korean"]),
    _place("mock-gastown-burger", "Gastown Burger", "Burgers", 2, 4.1, "310 Water St", "Vancouver", "A casual burger room in Gastown.", ["Burgers"]),
]


class MockRestaurantProvider(RestaurantProvider):
    """Curated places so local development works with no Geoapify key."""

    def collect(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
        return _materialize(intent)

    def search(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
        pool = dedupe_restaurants(self.collect(intent))
        constrained = apply_hard_constraints(pool, intent)
        ranked = rank_candidates(constrained, intent)
        if intent.cuisines:
            matched = [item for item in ranked if cuisine_matches(item.restaurant, intent)]
            if matched:
                ranked = matched
        deck = [item.restaurant for item in select_diverse_deck(ranked)]
        if len(deck) >= TARGET_COUNT:
            return deck[:TARGET_COUNT]
        return _pad(deck, self.collect(intent))


def _materialize(intent: DinnerIntent) -> list[RestaurantCandidate]:
    city = _known_city(intent.location)
    if city:
        selected = [item for item in _CATALOG if item["city"].lower() == city]
        label = item_label(intent.location, city)
    elif intent.location:
        selected = [item for item in _CATALOG if item["city"].lower() == "burnaby"]
        label = intent.location
    else:
        selected = [item for item in _CATALOG if item["city"].lower() == "vancouver"]
        label = "Vancouver"
    center = CITY_CENTERS.get(city or "vancouver", CITY_CENTERS["vancouver"])
    restaurants: list[RestaurantCandidate] = []
    for index, item in enumerate(selected):
        description = item["description"]
        if intent.vibe and intent.vibe.lower() not in description.lower() and item["vibe"] == intent.vibe.lower():
            description = f"{description} Fits a {intent.vibe} night."
        latitude = round(center[0] + ((index % 5) - 2) * 0.003, 6)
        longitude = round(center[1] + ((index % 3) - 1) * 0.003, 6)
        restaurants.append(
            RestaurantCandidate(
                external_id=item["external_id"],
                name=item["name"],
                description=description,
                cuisine=item["cuisine"],
                categories=list(item["categories"]),
                price=item["price"],
                rating=item["rating"],
                latitude=latitude,
                longitude=longitude,
                address=f"{item['street']}, {label}",
                image_url=None,
                source="mock",
            )
        )
    return restaurants


def item_label(location: str | None, city: str) -> str:
    if location and city in location.lower():
        return location
    return city.title()


def _known_city(location: str | None) -> str | None:
    if not location:
        return None
    text = location.lower()
    for city in CITY_CENTERS:
        if city in text:
            return city
    return None


def _pad(primary: list[RestaurantCandidate], backup: list[RestaurantCandidate]) -> list[RestaurantCandidate]:
    names = {item.name.lower() for item in primary}
    combined = list(primary)
    for item in backup:
        if item.name.lower() in names:
            continue
        names.add(item.name.lower())
        combined.append(item)
        if len(combined) >= TARGET_COUNT:
            break
    return combined
