# Nomly

Stop arguing. Let the group decide.

Nomly is a small multiplayer dinner picker. A host describes the night, friends join a room, everyone swipes the same restaurants in private, and a Python matching engine ranks the places the group actually agrees on.

Nomly does not require Docker for local development.

## Problem

Groups get stuck debating restaurants. One person likes the idea, someone else has a constraint, and the thread never ends.

## Solution

Everyone swipes independently on one shared list. Nomly does not show individual choices during the round. When the group is finished, it ranks restaurants by how many people liked them.

## MVP flow

```text
Describe Dinner
      ↓
AI Intent Parsing
      ↓
Restaurant Search
      ↓
Structured Ranking
      ↓
Semantic Ranking, when embeddings exist
      ↓
Create Room
      ↓
Friends Join
      ↓
Everyone Swipes
      ↓
Python Matching Engine
      ↓
Group Match
```

You can run this whole path with no Gemini or Geoapify key. The API falls back to `MockAIService` and `MockRestaurantProvider`.

Gemini reads the dinner description and returns a `DinnerIntent`: group size, location, radius, cuisines, price level, vibe, and dietary preferences. It does not look up restaurants. Phase 2 search does that. If Gemini is unavailable or returns invalid JSON, the deterministic parser is used and the room is still created. Set `GEMINI_API_KEY` in the backend `.env` to try a live call. The test suite never calls Gemini.

```text
We're five students looking for something cheap around Burnaby, preferably Japanese or Korean, and somewhere casual.
```

That request becomes Japanese and Korean, Burnaby, a low price level, a casual vibe, and a group size of five. Fields the user did not mention stay empty. A location or group size entered in the form overrides the description.

## Tech stack

- Next.js, React, TypeScript, Tailwind CSS, Framer Motion
- Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- MySQL or TiDB Cloud
- Gemini for intent parsing, when a key is configured
- Geoapify Places for restaurants, when a key is configured
- FastAPI WebSockets

## Setup

Install Node.js, npm, Python 3.11+, and pip. Install MySQL 8 locally, or use a TiDB Cloud database. Do not start a container for this project.

### Database

Create a database and user in MySQL:

```sql
CREATE DATABASE dineoff CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'dineoff'@'localhost' IDENTIFIED BY 'dineoff';
GRANT ALL PRIVILEGES ON dineoff.* TO 'dineoff'@'localhost';
FLUSH PRIVILEGES;
```

Copy the example environment file to the repository root:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Set `DATABASE_URL`:

```env
DATABASE_URL=mysql+pymysql://dineoff:dineoff@localhost:3306/dineoff
```

For TiDB Cloud, use the host from the TiDB console and include `ssl=true`. Hosts on `tidbcloud.com` also turn SSL on automatically:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@gateway01.example.prod.aws.tidbcloud.com:4000/dineoff?ssl=true
```

Leave `GEMINI_API_KEY` and `GEOAPIFY_API_KEY` empty until you have credentials. The app still runs.

`NEXT_PUBLIC_API_URL` is the only value the browser needs. The frontend defaults to `http://localhost:8000` if it is unset. Do not put `DATABASE_URL`, `GEMINI_API_KEY`, or `GEOAPIFY_API_KEY` in frontend code.

### Backend

```bash
cd backend
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

macOS and Linux:

```bash
source .venv/bin/activate
```

Install dependencies, apply migrations, and start the API:

```bash
pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

The API listens on `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

### Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The app listens on `http://localhost:3000`.

Optional, if you want the URL explicit:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Put that in `frontend/.env.local`.

## Running

Keep the two processes separate.

```text
Frontend:  http://localhost:3000
Backend:   http://localhost:8000
```

1. Open Create dinner and describe the meal. You get a room code such as `AB7KQ2`.
2. Friends open Join dinner, enter the code and a nickname, and land in the lobby.
3. Only the host can start. Starting opens the same restaurant deck for everyone.
4. Each person swipes Like or Pass. The room sees how many people have finished, not who liked what.
5. When everyone finishes, the match screen shows the group result.

A browser tab remembers its temporary name for that tab only, so you can demo several people from one computer by using separate windows or tabs.

## Testing

From `backend`, with the virtual environment active:

```bash
python -m pytest
```

The tests cover sessions, room codes, joining, host authorization, restaurant normalization, deduplication, relevance ranking, deck diversity, mock and Geoapify fallbacks, dinner-intent extraction, Gemini response validation, Gemini failure fallback, swipes, the 80% match case, ranking ties, WebSocket events, grounded semantic text, mock embeddings, combined ranking, and semantic fallback. They do not call live Gemini, Geoapify, or TiDB Cloud.

## Architecture

The backend is one FastAPI application.

```text
AIService
├── GeminiAIService
└── MockAIService

RestaurantProvider
├── GeoapifyRestaurantProvider
└── MockRestaurantProvider
```

`RestaurantProvider` is the only restaurant source the rest of the app sees. Geoapify stays behind it. A missing `GEOAPIFY_API_KEY` or a failed Geoapify request falls back to `MockRestaurantProvider`. The key is never sent to the browser.

When a dinner is created, one search builds the shared deck:

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

The deck is usually 10 to 15 places. If only a few restaurants fit, the room gets those few. Budget and radius are hard limits when the provider actually has that data. A stated diet removes a labeled place that misses it when another labeled place satisfies it. Missing labels are kept. That is not an allergy or safety claim. Cuisine, rating, and vibe affect the structured score: cuisine 40, price 25, location 15, rating 15, and category or vibe 5.

Soft preferences such as cozy or quiet are a separate step. The semantic query is the vibe only, so cuisine, budget, and location stay in the structured score. When restaurant embeddings already exist, the final order is 75% structured relevance and 25% normalized cosine similarity. Semantic ranking never puts a filtered restaurant back into the deck. If embeddings are missing, the embedding API fails, or TiDB vector search fails, the deck stays on the structured ranking and the room is still created.

`backend/app/services/matching/matching_service.py` ranks a finished room.

A pass scores 0, a like scores 1, and a super like scores 2. Each person gets one super like and one veto. A veto removes that restaurant from the winning set even if other people super liked it. Places over the stated budget, past a known distance limit, or missing a stated diet are also ineligible. The least-satisfied person is considered before extra enthusiasm, so five ordinary likes beat two super likes and three passes.

Example: 5 people and 4 likes is still 80%. The result explains the counts without naming who chose what. Unused super likes and vetoes are allowed.

Restaurants are fetched once when the room is created and reused for every swipe. See `docs/architecture.md` for the data model and socket events.

## Environment variables

| Variable | Where it is used | Required |
| --- | --- | --- |
| `DATABASE_URL` | Backend, MySQL or TiDB | Yes |
| `GEMINI_API_KEY` | Backend only. Intent parsing and embeddings | No |
| `GEOAPIFY_API_KEY` | Backend only | No |
| `EMBEDDING_MODEL` | Backend only. Defaults to `gemini-embedding-001` | No |
| `FRONTEND_URL` | Backend CORS for a deployed frontend | No |
| `NEXT_PUBLIC_API_URL` | Frontend | No, defaults to `http://localhost:8000` |
| `CORS_ORIGINS` | Backend | No |

`.env.example` lists them. `.env` is gitignored. Do not create `NEXT_PUBLIC_` copies of the Gemini, Geoapify, or database credentials.

## TiDB and embeddings

TiDB Cloud is the production MySQL-compatible database. The same `restaurants` table stores a grounded description, a hash of that description, a JSON embedding, and, on TiDB, a `VECTOR(768)` column. There is no second restaurant database.

From `backend`, with `DATABASE_URL` set:

```bash
python -m alembic upgrade head
python -m app.services.restaurants.refresh_embeddings
```

`upgrade head` adds the semantic columns. On a TiDB server it also adds the vector column and a cosine index. Downgrade removes only those columns.

The refresh command embeds restaurants whose text is missing or whose hash changed, and it skips the rest. Room creation does not embed the catalog. It embeds the vibe only when at least one candidate already has a vector.

Local MySQL and the test database do not need the vector column. They use the JSON embedding when it exists, and otherwise keep Phase 2 ranking. Leave `GEMINI_API_KEY` blank to use deterministic mock embeddings for that refresh.

Similarity is cosine. TiDB returns `VEC_COSINE_DISTANCE`, which is `1 - cosine`. Nomly maps cosine from [-1, 1] to [0, 1] before blending. The browser never receives vectors or raw similarity.

## Future roadmap

These are deliberately not in the MVP. The service boundaries are there so they can be added later:

- Ranked choice, consensus scoring, and richer tie breaks
- Meet-in-the-middle routing based on travel time
- Anonymous taste memory across sessions
- An ElevenLabs voice concierge
- Richer Gemini explanations

Also out of scope: accounts, passwords, payments, notifications, an admin dashboard, analytics, allergy guarantees, Redis, Kafka, RabbitMQ, microservices, and Docker.
