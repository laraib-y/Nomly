# DineOff architecture

DineOff is one Next.js app and one FastAPI app. They run as separate processes. There is no Docker, message bus, or extra service.

```text
Browser
  |  HTTP + WebSocket
  v
FastAPI
  |-- AIService -------- GeminiAIService or MockAIService
  |-- RestaurantProvider  GeoapifyRestaurantProvider or MockRestaurantProvider
  |-- SessionService
  |-- MatchingService
  v
MySQL or TiDB Cloud
```

## Request path

1. The host describes dinner. `SessionService` asks `AIService` for a `DinnerIntent`.
2. Pydantic validates that intent. The raw model text is never interpolated into SQL.
3. `RestaurantSearchService` asks `RestaurantProvider` for candidates, then normalizes, deduplicates, applies hard constraints, ranks, and stores one diverse deck of up to 15 restaurants. Swiping reads that stored deck.
4. Friends join with a room code and a nickname. There are no accounts.
5. The host starts the dinner. Connected browsers receive `dinner_started` and open the same deck.
6. Swipes are private. The socket only broadcasts how many people have finished.
7. When everyone has swiped every restaurant, `MatchingService` ranks the deck and the room receives `results_ready`.

## Service boundaries

`AIService`

- `GeminiAIService` calls Gemini and validates JSON into `DinnerIntent`.
- `MockAIService` is a deterministic keyword parser.
- If the Gemini key is missing, or the call fails, the mock parser is used.

`RestaurantProvider`

The rest of the app never calls Geoapify directly. Routes and the session service talk to `RestaurantProvider`, so a different place source can replace Geoapify without changing rooms, swipes, or matching.

```text
Dinner Intent
    ↓
Restaurant Search Service
    ↓
Geoapify Provider
    ↓
Normalization
    ↓
Deduplication
    ↓
Hard Constraints
    ↓
Relevance Ranking
    ↓
Diversity Selection
    ↓
10–15 Restaurant Deck
```

- `GeoapifyRestaurantProvider` geocodes the dinner location and searches restaurant categories that match the intent. Japanese in Burnaby is a different query from Italian in Vancouver.
- `MockRestaurantProvider` is a curated catalog used when `GEOAPIFY_API_KEY` is missing or Geoapify returns an expected failure. The catalog still follows cuisine, price, and city, so local development can tell those searches apart.
- A short real result is kept as-is. The deck is not padded with unrelated places just to reach 15. The older `search()` helper used by provider tests may still pad a failed live call so a demo never opens an empty room.
- Hard filters drop a known price above the budget and, when a center point exists, a place outside the radius. Missing price or coordinates are kept. Dietary words only affect ranking when the provider already labeled the place, and they are not an allergy or safety guarantee.
- Ranking is a weighted score, not the group matcher: cuisine 40, price 25, location 15, rating 15, vibe or category 5. Diversity then spreads cuisines inside that ranked set.
- The Geoapify key stays on the server. Logs redact `apiKey`.

`DinnerIntent` carries `group_size`, `location`, `radius`, `cuisines`, `price_level`, `vibe`, and `dietary_preferences`. Group size is a planning hint. The match still uses the people who actually joined.

`MatchingService`

- `compatibility = likes / total participants`
- Sort by compatibility, then likes, then rating, then name.
- The function is isolated so later fairness or travel-time rules can replace it without changing the API.

## Realtime

`/ws/sessions/{room_code}` sends:

- `state`
- `participant_joined`
- `participant_left`
- `dinner_started`
- `swipe_progress`
- `all_completed`
- `results_ready`

Progress messages contain counts only. They do not say who liked which restaurant.

## Data model

- `sessions` holds the room, description, host, and status (`lobby`, `active`, `completed`).
- `participants` belong to one session.
- `restaurants` stores normalized places. The same external place can be reused.
- `session_restaurants` attaches one ordered deck to a session. This join table is what keeps swipe order identical for the group.
- `swipes` stores `like` or `pass`, with a unique constraint on session, participant, and restaurant.

`host_participant_id` is stored on the session and checked in the service. It is not a database foreign key, because the session and its host row are created together.

## Intentionally not built

Vetoes, super-likes, accounts, payments, notifications, vector search, taste memory, travel-time routing, and ElevenLabs are extension points only. They are not part of this MVP.
