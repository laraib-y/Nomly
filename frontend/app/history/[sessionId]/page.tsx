"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ResultsDisplay } from "@/components/ResultsDisplay";
import { ApiError, getHistoryDinner } from "@/lib/api";
import { formatDinnerDate } from "@/lib/history";
import { NOT_AVAILABLE } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";
import type { HistoryDetail } from "@/types";

export default function HistoryDinnerPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { user } = useRequireUser();
  const [dinner, setDinner] = useState<HistoryDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !sessionId) return;
    let cancelled = false;
    getHistoryDinner(sessionId)
      .then((body) => {
        if (!cancelled) setDinner(body);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError && err.status === 404 ? "We couldn't find that dinner in your history." : err instanceof Error ? err.message : "Could not load this dinner");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, user]);

  if (error) {
    return (
      <section className="mx-auto max-w-lg pt-16 text-center">
        <h1 className="font-serif text-4xl">Dinner not found</h1>
        <p className="mt-3 text-ink-soft">{error}</p>
        <Link href="/history" className="button-secondary mt-8 inline-block rounded-full px-6 py-3">
          Back to your dinners
        </Link>
      </section>
    );
  }
  if (!user || !dinner) return <p className="pt-16 text-center text-ink-soft">Opening this dinner...</p>;

  const facts: [string, string][] = [
    ["Date", formatDinnerDate(dinner.created_at)],
    ["Location", dinner.location ?? NOT_AVAILABLE],
    ["Planned group", dinner.group_size === null ? NOT_AVAILABLE : `${dinner.group_size} people`],
    ["Took part", dinner.participant_count === 1 ? "1 person" : `${dinner.participant_count} people`],
    ["Restaurants considered", String(dinner.restaurant_count)],
  ];

  return (
    <section className="mx-auto max-w-2xl pt-2">
      <Link href="/history" className="text-sm text-ink-soft underline underline-offset-4">
        ← Your dinners
      </Link>

      <div className="form-panel mt-4 p-5 sm:p-6">
        <p className="text-xs uppercase tracking-[0.18em] text-ink-soft">What the group asked for</p>
        <blockquote className="mt-2 font-serif text-xl leading-snug">&ldquo;{dinner.description}&rdquo;</blockquote>
        <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-3">
          {facts.map(([label, value]) => (
            <div key={label} className="min-w-0">
              <dt className="text-ink-soft">{label}</dt>
              <dd className="break-words text-ink">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="mt-8">
        {dinner.results.top_match ? (
          <ResultsDisplay results={dinner.results} eyebrow="Where your group went" />
        ) : (
          <p className="text-center text-ink-soft">This dinner finished without a winner.</p>
        )}
      </div>
    </section>
  );
}
