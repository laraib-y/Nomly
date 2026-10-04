"use client";

import Link from "next/link";
import { motion } from "framer-motion";

import { FoodPhoto } from "@/components/RestaurantInfo";
import { cuisineBars, describeHistoryItem } from "@/lib/history";
import type { HistoryItem } from "@/types";

export function StatTile({ value, label, hint }: { value: string; label: string; hint?: string }) {
  return (
    <div className="min-w-0 px-2 text-center">
      <p className="font-serif text-4xl leading-none sm:text-5xl">{value}</p>
      <p className="mt-2 text-sm text-ink-soft">{label}</p>
      {hint ? <p className="mt-0.5 text-[11px] leading-tight text-ink-soft/80">{hint}</p> : null}
    </div>
  );
}

/** "What your groups eat": winner cuisines, longest bar first. */
export function CuisineBars({ cuisines }: { cuisines: { label: string; count: number }[] }) {
  const bars = cuisineBars(cuisines);
  if (!bars.length) return null;
  return (
    <ul className="space-y-2.5" aria-label="Winning cuisines">
      {bars.map((bar, index) => (
        <li key={bar.label} className="grid grid-cols-[7.5rem_1fr_auto] items-center gap-3 text-sm">
          <span className="truncate">
            <span aria-hidden="true">{bar.emoji}</span> {bar.label}
          </span>
          <span className="h-3 overflow-hidden rounded-full bg-paper-deep">
            <motion.span
              className="block h-full rounded-full bg-croc"
              initial={{ width: 0 }}
              animate={{ width: `${bar.width}%` }}
              transition={{ delay: 0.1 + index * 0.06, duration: 0.6, ease: "easeOut" }}
            />
          </span>
          <span className="w-6 text-right text-ink-soft">{bar.count}</span>
        </li>
      ))}
    </ul>
  );
}

export function HistoryCard({ item, index = 0 }: { item: HistoryItem; index?: number }) {
  const text = describeHistoryItem(item);
  const winner = item.winner;
  return (
    <motion.li
      className="min-w-0"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 8) * 0.04 }}
    >
      <Link
        href={`/history/${item.session_id}`}
        className="feature-card flex gap-4 rounded-3xl border border-line bg-card p-4 sm:p-5"
      >
        {winner ? (
          <FoodPhoto restaurant={winner} compact className="h-20 w-20 shrink-0 rounded-2xl sm:h-24 sm:w-24" />
        ) : (
          <span className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-paper-deep text-3xl sm:h-24 sm:w-24">
            🍽️
          </span>
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate font-serif text-2xl leading-tight" title={text.title}>
            <span aria-hidden="true">{text.emoji}</span> {text.title}
          </p>
          <p className="truncate text-sm text-ink-soft">{text.subtitle}</p>
          <p className="mt-2 text-moss">{text.satisfaction}</p>
          {item.satisfaction_percent !== null ? (
            <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-paper-deep" aria-hidden="true">
              <span className="block h-full rounded-full bg-moss" style={{ width: `${item.satisfaction_percent}%` }} />
            </span>
          ) : null}
          <p className="mt-2 text-sm text-ink-soft">{text.meta}</p>
        </div>
      </Link>
    </motion.li>
  );
}
