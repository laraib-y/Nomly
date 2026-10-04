"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CuisineBars, HistoryCard, StatTile } from "@/components/HistoryPieces";
import { SatisfactionTimeline } from "@/components/SatisfactionTimeline";
import { getHistory } from "@/lib/api";
import { NOT_AVAILABLE } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";
import type { HistoryList } from "@/types";

export default function HistoryPage() {
  const { user } = useRequireUser();
  const [history, setHistory] = useState<HistoryList | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    getHistory()
      .then((body) => {
        if (!cancelled) setHistory(body);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load your dinners");
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  if (!user || (!history && !error)) {
    return <p className="pt-16 text-center text-ink-soft">Gathering your dinners...</p>;
  }
  if (error || !history) {
    return <p className="form-error pt-16 text-center">{error}</p>;
  }

  const { items, stats, cuisines } = history;

  if (!items.length) {
    return (
      <section className="mx-auto max-w-lg pt-12 text-center">
        <p className="text-5xl" aria-hidden="true">
          🍽️
        </p>
        <h1 className="mt-4 font-serif text-5xl">Your Dinners</h1>
        <p className="mt-4 text-lg text-ink-soft">
          No finished dinners yet. Create one while you&apos;re logged in and it lands here once everyone has swiped.
        </p>
        <Link href="/create" className="button-primary mt-8 inline-block rounded-full px-6 py-3">
          Create a dinner
        </Link>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-3xl pt-4">
      <h1 className="text-center font-serif text-5xl sm:text-6xl">Your Dinners</h1>

      <div className="mt-8 grid grid-cols-2 gap-y-6 border-b border-line pb-8 sm:grid-cols-4">
        <StatTile value={String(stats.dinners)} label={stats.dinners === 1 ? "Dinner" : "Dinners"} />
        <StatTile
          value={String(stats.strong_matches)}
          label={stats.strong_matches === 1 ? "Strong match" : "Strong matches"}
          hint="Two-thirds or more liked the winner"
        />
        <StatTile
          value={stats.average_satisfaction_percent === null ? "–" : `${stats.average_satisfaction_percent}%`}
          label="Average satisfaction"
          hint={stats.average_satisfaction_percent === null ? NOT_AVAILABLE : undefined}
        />
        <StatTile
          value={stats.average_group_size === null ? "–" : String(stats.average_group_size)}
          label="Average group size"
        />
      </div>

      <div className="form-panel mt-8 p-5 sm:p-8">
        <h2 className="font-serif text-2xl sm:text-3xl">How well do your groups agree?</h2>
        <p className="mt-1 text-sm text-ink-soft">
          Every dot is a dinner. Higher means more of the table liked where you ended up. Tap one to see it.
        </p>
        <div className="mt-6">
          <SatisfactionTimeline items={items} />
        </div>
      </div>

      {cuisines.length ? (
        <div className="mt-8 px-1">
          <h2 className="font-serif text-2xl">What your groups eat</h2>
          <div className="mt-4">
            <CuisineBars cuisines={cuisines} />
          </div>
        </div>
      ) : null}

      <h2 className="mt-10 font-serif text-3xl">Recent dinners</h2>
      <ul className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {items.map((item, index) => (
          <HistoryCard key={item.session_id} item={item} index={index} />
        ))}
      </ul>
    </section>
  );
}
