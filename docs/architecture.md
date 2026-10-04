# Nomly architecture

Nomly is one Next.js app and one FastAPI app. They run as separate processes. There is no Docker, message bus, or extra service.

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

1. The host describes dinner in plain language, by typing or by speaking. Speech is transcribed at `POST /api/voice/transcribe` and the text is sent through the same `POST /api/sessions` path. `SessionService` asks `AIService` for a `DinnerIntent`.
2. Pydantic validates that intent. The raw model text is never interpolated into SQL. Explicit location and group size from the form replace anything the parser inferred for those fields.
3. `RestaurantSearchService` asks `RestaurantProvider` for candidates, then normalizes, deduplicates, applies hard constraints, ranks, and stores one diverse deck of up to 15 restaurants. Swiping reads that stored deck.
4. Friends join with a room code and a nickname. There are no accounts.
5. The host starts the dinner. Connected browsers receive `dinner_started` and open the same deck.
6. Swipes are private. The socket only broadcasts how many people have finished.
7. When everyone has swiped every restaurant, `MatchingService` ranks the deck and the room receives `results_ready`.

## Service boundaries

`AIService`

Gemini only turns the description into structured search intent. It does not search Geoapify, name restaurants, rank a deck, or decide the group match.

```text
User's natural-language request
        ↓
GeminiAIService or MockAIService
        ↓
DinnerIntent, validated by Pydantic
        ↓
Restaurant Search Service
        ↓
Geoapify or the mock catalog
        ↓
Hard constraints and structured ranking
        ↓
TiDB vector search, when embeddings exist
        ↓
Restaurant deck
        ↓
Phase 4 group matcher
```

- `GeminiAIService` calls Gemini with a backend `GEMINI_API_KEY` and requires JSON that validates as `DinnerIntent`.
- `MockAIService` is a deterministic parser. Tests and local runs use it whenever the key is missing.
- A timeout, rate limit, network error, malformed JSON, or validation failure is logged on the server and parsed again with `MockAIService`. The API response does not include the provider error.
- Missing details stay null or empty. A radius is stored only when the request states a distance, in meters. Restaurant search uses 5000 meters when radius is null.
- Dietary labels are preferences, not an allergy or safety guarantee.

`DinnerIntent` carries `group_size`, `location`, `radius`, `cuisines`, `price_level`, `vibe`, and `dietary_preferences`. Group size is a planning hint. The match still uses the people who actually joined.

Example:

```text
We're five students looking for something cheap around Burnaby, preferably Japanese or Korean, and somewhere casual.
```

```json
{
  "group_size": 5,
  "location": "Burnaby",
  "radius": null,
  "cuisines": ["Japanese", "Korean"],
  "price_level": 1,
  "vibe": "casual",
  "dietary_preferences": []
}
```

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
Structured Ranking
    ↓
Semantic Ranking
    ↓
Diversity Selection
    ↓
10–15 Restaurant Deck
```

- `GeoapifyRestaurantProvider` geocodes the dinner location and searches restaurant categories that match the intent. Japanese in Burnaby is a different query from Italian in Vancouver.
- `MockRestaurantProvider` is a curated catalog used when `GEOAPIFY_API_KEY` is missing or Geoapify returns an expected failure. The catalog still follows cuisine, price, and city, so local development can tell those searches apart.
- A short real result is kept as-is. The deck is not padded with unrelated places just to reach 15. The older `search()` helper used by provider tests may still pad a failed live call so a demo never opens an empty room.
- Hard filters drop a known price above the budget and, when a center point exists, a place outside the radius. A stated diet drops a labeled place that misses it when another labeled place satisfies it. Missing price, coordinates, or labels are kept. This is not an allergy or safety guarantee.
- Structured ranking is a weighted score, not the group matcher: cuisine 40, price 25, location 15, rating 15, vibe or category 5.
- Semantic ranking runs after that filter. The query text is `DinnerIntent.vibe` only. Cuisine, budget, and location are not embedded, so vector similarity cannot relax them. The blend is `0.75 * structured + 0.25 * semantic`. Semantic scores are cosine similarity mapped from [-1, 1] to [0, 1]. TiDB computes `VEC_COSINE_DISTANCE` (`1 - cosine`) over the eligible restaurant ids. Local databases without a vector column use the same cosine math on `embedding_json`.
- If no candidate has an embedding, the embedding request fails, or the TiDB query fails, the structured order is kept and room creation continues. Logs say `Semantic search unavailable; using structured ranking fallback`. They do not include keys or vectors.
- Restaurant embeddings are built from stored fields only: name, cuisine, price, rating, address, categories, and description. Refresh them with `python -m app.services.restaurants.refresh_embeddings`. A changed text hash clears the old vector. Creating a room does not call the embedding API for the catalog.
- Diversity then spreads cuisines inside the ranked set.
- The Geoapify key and the embedding key stay on the server. Logs redact `apiKey`.

`MatchingService`

Phase 4 ranks the shared deck after everyone has chosen. Gemini does not pick the winner.

Each person can pass, like, super like once, or veto once. A higher rating breaks an otherwise equal result.

Satisfaction is 0 for a pass, 1 for a like, and 2 for a super like. A veto, a known price above the budget, a known distance past the requested radius, or a labeled place that misses a stated diet cannot win. Missing price, distance, or labels are not treated as violations, and a diet label is not an allergy guarantee.

Eligible places sort by the least-satisfied person, then average satisfaction, then super likes, likes, Phase 2 relevance, rating, and restaurant id. The same inputs always produce the same ranking.

```text
Restaurant A: two Super Likes and three passes
Restaurant B: five Likes
```

B wins. A is more exciting for two people, and B is acceptable to everyone.

Explanations are built in Python from counts only. They can say that a place was eliminated by a group veto. They do not name who liked or vetoed it.

### Phase 6.2: Matching transparency and result consistency

Problem found. A winner could show 67% while an alternative showed 100%, and the card could say "2 of 3 liked" while the explanation said "3 of 3 positive". The percentage was `likes / participants`, so it ignored Super Likes. The explanation counted Like and Super Like as positive. The ranking used the 0 to 2 satisfaction values. Three parts of the result used three different meanings. The ranking itself was correct.

Canonical definitions, used by the API, the explanation, and the UI:

```text
PASS = 0   LIKE = 1   SUPER LIKE = 2   VETO = not a score, removes the place

positives            = likes + super_likes
satisfaction_percent = positives / participants                       (Phase 6.2.1)
passes               = participants - likes - super_likes - vetoes   (no choice counts as a pass)
```

**Group satisfaction** represents the percentage of participants who selected Like or Super Like. The matching engine continues to use the existing weighted preference values (Pass = 0, Like = 1, Super Like = 2) for fairness ranking.

So 3/3 positive is always 100%, whether the votes were Likes or Super Likes. 2 Likes and 1 Pass is 67%. 1 Like and 2 Passes is 33%. `compatibility_percent` carries the same number for older clients. The weighted values appear only as `fairness.least_satisfied_percent` and `fairness.average_satisfaction_percent`, each out of a maximum of 2 per person. Each result also has `positives`, `elimination_reason`, `rank`, and `highlight`. No field identifies a participant.

The ranking is unchanged. It still sorts by the least-satisfied person first, then the weighted average, so a higher Group satisfaction can lose:

```text
Calm Kitchen: 6 Likes + 1 Super Like          100%, everyone positive
Loud Grill:   6 Super Likes + 1 Pass           86%, one person passed      -> Calm Kitchen wins on balance

Keen Taqueria: 2 Super Likes + 2 Passes        50%
Wide Bistro:   3 Likes + 1 Pass                75%                          -> Keen Taqueria wins on stronger support
```

Both of the second pair had someone pass, so balance ties and the weighted average decides: 4 points against 3. A 100% place can only lose by breaking a hard limit or being vetoed, and the explanation says which.

"Why this won" compares the winner with the ranking's own criteria, in order. If an eligible alternative had higher Group satisfaction, it names that alternative and the criterion that beat it: balance (someone passed on it) or stronger overall support (Super Likes). If a higher place was not eligible, it says why. Otherwise it gives the deciding factor: balance, Group satisfaction, stronger support, Super Likes, Likes, relevance, rating, or the fixed tie-break. The results page labels the winner "Best overall balance" or "Strongest overall support", and those alternatives "Higher satisfaction", only when that is true. It shows vetoed or out-of-limit places as "Not eligible" without saying who.

Tests: `backend/tests/test_result_transparency.py` and `frontend/tests/results.test.ts`.

The swipe socket still sends `swipe_progress`, `all_completed`, and `results_ready`. Progress adds how many super likes and vetoes have been used, not who used them.

### Phase 7.1: Restaurant information cards

Cards show only what the provider gave us. Geoapify supplies the name, a formatted address, coordinates, categories (which the pipeline turns into `cuisine`), and, for many places, `contact.phone` and `website`. In a 40-place Burnaby sample, every place had an address and coordinates, about two thirds had a phone or website, and none had a rating, price level, or photo. `phone` and `website` are new nullable columns on `restaurants` (migration `0005_restaurant_contact`). The backend keeps a website or image only if it is a plain `http(s)` URL, and a phone only if it has 7 to 15 digits. The frontend checks URLs again before rendering a link.

Any missing field shows "Not available for now". Price is shown only for a provider level from 1 to 4, and rating only for a provider value from 0 to 5. Nothing is inferred from the cuisine or the restaurant name. The map link uses the restaurant's own coordinates, never the user's.

Images follow this order: a provider photo, then a cuisine photo from `frontend/public/food`, then a generic food photo. The cuisine comes from the pipeline's `cuisine` and `categories`, not from the restaurant name. When a cuisine has more than one photo, the restaurant id picks one, so a place keeps the same picture on the deck and on results. Cuisine and generic photos are labelled "Representative photo". The code is in `frontend/lib/foodImages.ts` and `frontend/lib/format.ts`.

### Phase 8: Accounts and dinner history

Accounts are optional. Guests still create, join, and swipe with only a nickname, exactly as before.

- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`. Responses carry `id`, `email`, `display_name`, and `created_at`. Password hashes never leave the server.
- Passwords are hashed with Argon2id (`argon2-cffi`). Login answers "Email or password is incorrect" for both a wrong password and an unknown email, and verifies against a dummy hash so the two take the same time.
- A successful login or registration stores a random 256-bit token in an `HttpOnly`, `SameSite=Lax` cookie named `nomly_session` that lasts 30 days. The database keeps only the token's SHA-256 in `auth_sessions`, with an expiry. Logout deletes that row, so an old cookie stops working at once. The frontend never sees the token and keeps nothing about the session in `localStorage` or `sessionStorage`.
- CSRF: the cookie is `SameSite=Lax`, and a middleware rejects any `POST`, `PUT`, `PATCH`, or `DELETE` that carries the cookie (or targets `/api/auth/*`) when its `Origin` is not an allowed frontend origin.
- Login is limited to 10 attempts per 5 minutes per IP and email. Registration is limited to 5 per 10 minutes per IP. The limiter is in-process, so it resets on restart and is per instance.
- A dinner created while signed in stores `sessions.user_id`. Guest dinners keep `NULL`. Joining someone else's room never changes the owner.
- `GET /api/history` and `GET /api/history/{session_id}` require a signed-in user and only read finished dinners where `sessions.user_id` is that user. Someone else's dinner, a guest dinner, an unfinished dinner, and an unknown id all return the same `404 Dinner not found`.
- History numbers come from the same results builder as the live results screen, so the satisfaction shown in history always matches what the group saw. Items carry aggregate counts only: no nicknames, participant ids, or individual votes.
- Stats: dinners, strong matches (at least two-thirds of the table chose Like or Super Like for the winner), average winner satisfaction, and average number of people who took part. Cuisine counts use the winner's cuisine and skip "Restaurant" or missing values.
- The `/history` timeline is plain SVG plus positioned buttons, with no chart library. Each dinner is placed by date and group satisfaction, and dinners without a satisfaction number are left out rather than drawn at 0%.

Cross-site deployments, where the site and the API are on different registrable domains, need `AUTH_COOKIE_SAMESITE=none`. That forces `Secure` on, so the API must be served over HTTPS. Same-site deployments keep the default `lax`. Set `AUTH_COOKIE_SECURE=true` whenever the API is on HTTPS.

Migration `0006_user_accounts` adds `users`, `auth_sessions`, and the nullable `sessions.user_id`. Existing dinners and restaurant rows are untouched. Tests: `backend/tests/test_auth_history.py`, `backend/tests/test_migration_0006.py`, `frontend/tests/account.test.ts`, and `frontend/tests/history.test.ts`.

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
- `restaurants` stores normalized places. The same external place can be reused. `semantic_text`, `semantic_text_hash`, and `embedding_json` describe that same row. TiDB may also store an `embedding VECTOR(768)` column. Clients do not receive those fields.
- `session_restaurants` attaches one ordered deck to a session. This join table is what keeps swipe order identical for the group.
- `swipes` stores `pass`, `like`, `super_like`, or `veto`. One row per participant and restaurant. A second unique key allows only one super like and one veto per participant in the room.
- `sessions.intent_json` keeps the parsed dinner intent so budget, diet, and radius can be enforced again at match time.
- `sessions.user_id` is the account that created the dinner, or `NULL` for guests. It is set to `NULL` if the account is deleted.
- `users` holds email (unique, lowercased), Argon2id `password_hash`, and `display_name`.
- `auth_sessions` holds one row per signed-in browser: the SHA-256 of the cookie token and its expiry.

`host_participant_id` is stored on the session and checked in the service. It is not a database foreign key, because the session and its host row are created together.

## Intentionally not built

Payments, notifications, profile editing, password reset, taste memory, and travel-time routing are extension points only. They are not part of this MVP. Semantic ranking is limited to soft preferences over restaurants that already passed the structured filters.
