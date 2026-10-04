import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import type { HistoryItem } from "../types/index.ts";

const history = await import("../lib/history.ts");
const { NOT_AVAILABLE } = await import("../lib/format.ts");
const { TIMELINE_BOX, cuisineBars, cuisineEmoji, describeHistoryItem, formatDinnerDate, percentToY, timelinePath, timelinePoints, timelineTicks } = history;

const NOW = new Date("2026-10-04T12:00:00Z");

function dinner(overrides: Partial<HistoryItem> = {}): HistoryItem {
  return {
    session_id: "s1",
    created_at: "2026-09-28T19:00:00",
    completed_at: "2026-09-28T19:20:00",
    description: "Korean near Burnaby",
    location: "Burnaby",
    group_size: 3,
    participant_count: 3,
    restaurant_count: 10,
    winner: { restaurant_id: "r1", name: "DooBoo", cuisine: "Korean", rating: null, price: null, address: null, image_url: null },
    satisfaction_percent: 100,
    positives: 3,
    ...overrides,
  };
}

// History rendering

test("a history card reads like the design: name, cuisine and place, satisfaction, people and date", () => {
  const text = describeHistoryItem(dinner(), "UTC", NOW);
  assert.deepEqual(text, {
    title: "DooBoo",
    emoji: "🍖",
    subtitle: "Korean · Burnaby",
    satisfaction: "100% group satisfaction",
    meta: "3 people · Sep 28",
  });
});

test("missing provider data stays honest", () => {
  const text = describeHistoryItem(
    dinner({
      location: null,
      participant_count: 1,
      satisfaction_percent: null,
      winner: { restaurant_id: "r2", name: "Mystery", cuisine: null, rating: null, price: null, address: null, image_url: null },
    }),
    "UTC",
    NOW,
  );
  assert.equal(text.subtitle, `Cuisine · ${NOT_AVAILABLE}`);
  assert.equal(text.satisfaction, `Group satisfaction · ${NOT_AVAILABLE}`);
  assert.equal(text.meta, "1 person · Sep 28");
  assert.equal(text.emoji, "🍽️");
});

test("dates show the year only when it is not this year", () => {
  assert.equal(formatDinnerDate("2026-09-01T10:00:00", "UTC", NOW), "Sep 1");
  assert.equal(formatDinnerDate("2025-12-24T10:00:00", "UTC", NOW), "Dec 24, 2025");
  assert.equal(formatDinnerDate("not a date", "UTC", NOW), NOT_AVAILABLE);
});

test("cuisine emoji follows the same cuisine mapping as the food photos", () => {
  assert.equal(cuisineEmoji("Japanese"), "🍣");
  assert.equal(cuisineEmoji("Pizza"), "🍝");
  assert.equal(cuisineEmoji(null), "🍽️");
});

// Visualization

test("timeline puts dinners in time order with 100% at the top and 0% at the bottom", () => {
  const items = [
    dinner({ session_id: "late", created_at: "2026-10-01T19:00:00", satisfaction_percent: 0 }),
    dinner({ session_id: "early", created_at: "2026-09-01T19:00:00", satisfaction_percent: 100 }),
    dinner({ session_id: "mid", created_at: "2026-09-16T19:00:00", satisfaction_percent: 50 }),
  ];
  const points = timelinePoints(items);
  assert.deepEqual(points.map((point) => point.item.session_id), ["early", "mid", "late"]);
  const { width, height, padX, padY } = TIMELINE_BOX;
  assert.equal(points[0].x, padX);
  assert.equal(points[2].x, width - padX);
  assert.equal(points[0].y, padY);
  assert.equal(points[2].y, height - padY);
  assert.equal(points[1].y, percentToY(50));
  assert.equal(points[1].x, (padX + (width - padX)) / 2);
});

test("timeline leaves out dinners without a satisfaction number instead of drawing them at zero", () => {
  const points = timelinePoints([dinner({ satisfaction_percent: null }), dinner({ session_id: "s2" })]);
  assert.deepEqual(points.map((point) => point.item.session_id), ["s2"]);
  assert.equal(points[0].x, TIMELINE_BOX.width / 2, "a single dinner sits in the middle");
  assert.equal(timelinePath(points), "", "no line for one dinner");
  assert.deepEqual(timelinePoints([]), []);
});

test("timeline path joins every dinner and stays inside the chart", () => {
  const items = [0, 1, 2, 3].map((day) =>
    dinner({ session_id: `d${day}`, created_at: `2026-09-0${day + 1}T19:00:00`, satisfaction_percent: day % 2 ? 100 : 0 }),
  );
  const points = timelinePoints(items);
  const path = timelinePath(points);
  assert.match(path, /^M /);
  assert.equal(path.match(/ C /g)?.length, 3);
  const numbers = path.match(/-?\d+(\.\d+)?/g)!.map(Number);
  const ys = numbers.filter((_, index) => index % 2 === 1);
  assert.ok(Math.min(...ys) >= TIMELINE_BOX.padY);
  assert.ok(Math.max(...ys) <= TIMELINE_BOX.height - TIMELINE_BOX.padY);
});

test("dinners on the same moment are spread out evenly", () => {
  const items = ["a", "b", "c"].map((id) => dinner({ session_id: id }));
  const xs = timelinePoints(items).map((point) => point.x);
  assert.deepEqual(xs, [TIMELINE_BOX.padX, TIMELINE_BOX.width / 2, TIMELINE_BOX.width - TIMELINE_BOX.padX]);
});

test("axis shows first, middle and last dates without repeats", () => {
  const items = [1, 2, 3, 4, 5].map((day) => dinner({ session_id: `d${day}`, created_at: `2026-09-0${day}T12:00:00` }));
  const ticks = timelineTicks(timelinePoints(items), "UTC", NOW);
  assert.deepEqual(ticks.map((tick) => tick.label), ["Sep 1", "Sep 3", "Sep 5"]);
  const same = timelineTicks(timelinePoints([dinner({ session_id: "a" }), dinner({ session_id: "b" })]), "UTC", NOW);
  assert.deepEqual(same.map((tick) => tick.label), ["Sep 28"]);
});

test("cuisine bars are relative to the most common cuisine", () => {
  assert.deepEqual(
    cuisineBars([
      { label: "Korean", count: 4 },
      { label: "Japanese", count: 2 },
      { label: "Thai", count: 1 },
    ]).map(({ label, width }) => [label, width]),
    [
      ["Korean", 100],
      ["Japanese", 50],
      ["Thai", 25],
    ],
  );
  assert.deepEqual(cuisineBars([]), []);
});

test("history uses hand-built SVG, Phase 7.1 photos, and no chart library", () => {
  const pkg = JSON.parse(readFileSync("package.json", "utf8"));
  const deps = Object.keys({ ...pkg.dependencies, ...pkg.devDependencies });
  assert.ok(!deps.some((name) => /chart|d3|recharts|visx|nivo|victory/.test(name)), deps.join(","));
  const timeline = readFileSync("components/SatisfactionTimeline.tsx", "utf8");
  assert.match(timeline, /<svg/);
  assert.match(timeline, /aria-label=\{`\$\{point\.item\.winner\?\.name/);
  assert.match(timeline, /onMouseEnter/);
  assert.match(timeline, /onClick/);
  const pieces = readFileSync("components/HistoryPieces.tsx", "utf8");
  assert.match(pieces, /<FoodPhoto restaurant=\{winner\}/);
  const page = readFileSync("app/history/page.tsx", "utf8");
  for (const text of ["Your Dinners", "<SatisfactionTimeline", "<CuisineBars", "Recent dinners", "No finished dinners yet"]) {
    assert.ok(page.includes(text), text);
  }
});

test("dinner detail shows the request, facts, winner and alternatives without people's names", () => {
  const page = readFileSync("app/history/[sessionId]/page.tsx", "utf8");
  for (const text of ["What the group asked for", "Location", "Planned group", "Took part", "Restaurants considered", "<ResultsDisplay"]) {
    assert.ok(page.includes(text), text);
  }
  assert.doesNotMatch(page, /nickname|participants\.map/);
  const display = readFileSync("components/ResultsDisplay.tsx", "utf8");
  assert.match(display, /Why this won/);
  assert.match(display, /Other options/);
});
