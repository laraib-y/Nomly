# DineOff

Stop arguing. Let the group decide.

DineOff is a small multiplayer dinner picker. A host describes the night, friends join a room, everyone swipes the same restaurants in private, and a Python matching engine ranks the places the group actually agrees on.

DineOff does not require Docker for local development.

## Problem

Groups get stuck debating restaurants. One person likes the idea, someone else has a constraint, and the thread never ends.

## Solution

Everyone swipes independently on one shared list. DineOff does not show individual choices during the round. When the group is finished, it ranks restaurants by how many people liked them.

## MVP flow

```text
Describe Dinner
      ↓
AI Intent Parsing
      ↓
Restaurant Search
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

The tests cover sessions, room codes, joining, host authorization, restaurant normalization, deduplication, relevance ranking, deck diversity, mock and Geoapify fallbacks, the mock AI parser, Gemini response validation, swipes, the 80% match case, ranking ties, and WebSocket events.

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
Relevance Ranking
    ↓
Diversity Selection
    ↓
10–15 Restaurant Deck
```

The deck is usually 10 to 15 places. If only a few restaurants fit, the room gets those few. Budget and radius are hard limits when the provider actually has that data. Cuisine, rating, and vibe affect the order. The score is cuisine 40, price 25, location 15, rating 15, and category or vibe 5. Dietary labels are a ranking hint only, never a safety claim.

`backend/app/services/matching/matching_service.py` ranks a restaurant with:

```text
compatibility = number of likes / total participants
```

Example: 5 people and 4 likes is 80%. Ties break on like count, then rating, then name.

Restaurants are fetched once when the room is created and reused for every swipe. See `docs/architecture.md` for the data model and socket events.

## Environment variables

| Variable | Where it is used | Required |
| --- | --- | --- |
| `DATABASE_URL` | Backend, MySQL or TiDB | Yes |
| `GEMINI_API_KEY` | Backend only | No |
| `GEOAPIFY_API_KEY` | Backend only | No |
| `NEXT_PUBLIC_API_URL` | Frontend | No, defaults to `http://localhost:8000` |
| `CORS_ORIGINS` | Backend | No |

`.env.example` lists them. `.env` is gitignored.

## Future roadmap

These are deliberately not in the MVP. The service boundaries are there so they can be added later:

- One veto and one super-like per person, plus fairer preference weighting
- Ranked choice, consensus scoring, and richer tie breaks
- Meet-in-the-middle routing based on travel time
- Review embeddings and TiDB Vector Search for vibes such as cozy, quiet, or good for groups
- Anonymous taste memory across sessions
- An ElevenLabs voice concierge
- Richer Gemini explanations

Also out of scope: accounts, passwords, payments, notifications, an admin dashboard, analytics, allergy guarantees, Redis, Kafka, RabbitMQ, microservices, and Docker.
