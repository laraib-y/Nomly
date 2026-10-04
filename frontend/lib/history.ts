import type { HistoryItem } from "../types/index.ts";
import { parseApiDate } from "./account.ts";
import { cuisineKey } from "./foodImages.ts";
import { NOT_AVAILABLE, formatCuisine } from "./format.ts";

export type TimelinePoint = {
  x: number;
  y: number;
  percent: number;
  item: HistoryItem;
};

export type TimelineBox = { width: number; height: number; padX: number; padY: number };

export const TIMELINE_BOX: TimelineBox = { width: 640, height: 240, padX: 44, padY: 20 };

const EMOJI: Record<string, string> = {
  korean: "🍖",
  japanese: "🍣",
  chinese: "🥟",
  indian: "🍛",
  mexican: "🌮",
  italian: "🍝",
  thai: "🍜",
  vietnamese: "🍜",
  mediterranean: "🥙",
  "middle eastern": "🥙",
  american: "🍔",
  seafood: "🦐",
  vegetarian: "🥗",
};

export function cuisineEmoji(cuisine: string | null | undefined) {
  const key = cuisineKey({ cuisine: cuisine ?? null });
  return (key && EMOJI[key]) || "🍽️";
}

export function formatDinnerDate(value: string, timeZone?: string, now = new Date()) {
  const date = parseApiDate(value);
  if (!date) return NOT_AVAILABLE;
  const sameYear = date.getUTCFullYear() === now.getUTCFullYear();
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: sameYear ? undefined : "numeric",
    timeZone,
  });
}

/** Text for one history card. Missing provider data says so instead of guessing. */
export function describeHistoryItem(item: HistoryItem, timeZone?: string, now = new Date()) {
  const winner = item.winner;
  const cuisine = formatCuisine(winner?.cuisine ?? null);
  const people = item.participant_count === 1 ? "1 person" : `${item.participant_count} people`;
  return {
    title: winner?.name ?? "No winner",
    emoji: cuisineEmoji(winner?.cuisine),
    subtitle: [cuisine ?? `Cuisine · ${NOT_AVAILABLE}`, item.location].filter(Boolean).join(" · "),
    satisfaction:
      item.satisfaction_percent === null ? `Group satisfaction · ${NOT_AVAILABLE}` : `${item.satisfaction_percent}% group satisfaction`,
    meta: `${people} · ${formatDinnerDate(item.created_at, timeZone, now)}`,
  };
}

/**
 * Places each finished dinner on a time axis (x) against its group satisfaction (y).
 * Dinners without a satisfaction number are left out rather than drawn at zero.
 */
export function timelinePoints(items: HistoryItem[], box: TimelineBox = TIMELINE_BOX): TimelinePoint[] {
  const dated = items
    .map((item) => ({ item, time: parseApiDate(item.created_at)?.getTime() ?? null }))
    .filter((entry): entry is { item: HistoryItem; time: number } => entry.time !== null && entry.item.satisfaction_percent !== null)
    .sort((a, b) => a.time - b.time);
  if (!dated.length) return [];

  const first = dated[0].time;
  const span = dated[dated.length - 1].time - first;
  const innerWidth = box.width - box.padX * 2;
  const innerHeight = box.height - box.padY * 2;

  return dated.map(({ item, time }, index) => {
    const percent = Math.min(100, Math.max(0, item.satisfaction_percent ?? 0));
    // Equal spacing when every dinner happened at the same moment, otherwise true time spacing.
    const share = span > 0 ? (time - first) / span : dated.length === 1 ? 0.5 : index / (dated.length - 1);
    return {
      x: round(box.padX + share * innerWidth),
      y: round(box.padY + (1 - percent / 100) * innerHeight),
      percent,
      item,
    };
  });
}

/** Soft curve through the points. Flat tangents at each dinner keep it from overshooting 0% or 100%. */
export function timelinePath(points: Pick<TimelinePoint, "x" | "y">[]) {
  if (points.length < 2) return "";
  let path = `M ${points[0].x} ${points[0].y}`;
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const midX = round((previous.x + current.x) / 2);
    path += ` C ${midX} ${previous.y} ${midX} ${current.y} ${current.x} ${current.y}`;
  }
  return path;
}

export function percentToY(percent: number, box: TimelineBox = TIMELINE_BOX) {
  return round(box.padY + (1 - percent / 100) * (box.height - box.padY * 2));
}

/** Up to three dates under the axis: first, middle, last. */
export function timelineTicks(points: TimelinePoint[], timeZone?: string, now = new Date()) {
  if (!points.length) return [];
  const picks = points.length <= 3 ? points : [points[0], points[Math.floor(points.length / 2)], points[points.length - 1]];
  const seen = new Set<string>();
  return picks.flatMap((point) => {
    const label = formatDinnerDate(point.item.created_at, timeZone, now);
    if (seen.has(label)) return [];
    seen.add(label);
    return [{ x: point.x, label }];
  });
}

export function cuisineBars(cuisines: { label: string; count: number }[]) {
  const max = Math.max(0, ...cuisines.map((entry) => entry.count));
  if (max === 0) return [];
  return cuisines
    .filter((entry) => entry.count > 0)
    .map((entry) => ({ ...entry, emoji: cuisineEmoji(entry.label), width: Math.round((entry.count / max) * 100) }));
}

function round(value: number) {
  return Math.round(value * 10) / 10;
}
