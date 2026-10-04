"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { cuisineWash, formatPrice, formatRating } from "@/lib/format";
import { getResults } from "@/lib/api";
import { useSession } from "@/lib/useSession";
import type { Results } from "@/types";

export function ResultsRoom({ roomCode }: { roomCode: string }) {
  const router = useRouter();
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showWhy, setShowWhy] = useState(false);
  const { session, progress, eventName } = useSession(roomCode);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const next = await getResults(roomCode);
        if (!cancelled) {
          setResults(next);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Results are not ready");
      }
    }

    void load();
    const poll = window.setInterval(() => void load(), 2500);
    return () => {
      cancelled = true;
      window.clearInterval(poll);
    };
  }, [roomCode, eventName]);

  useEffect(() => {
    if (session?.status === "lobby") router.replace(`/dinner/${roomCode}`);
  }, [roomCode, router, session]);

  const top = results?.top_match;
  if (!top) {
    return (
      <section className="mx-auto max-w-xl pt-16 text-center">
        <p className="text-sm uppercase tracking-[0.2em] text-gold">Still deciding</p>
        <h1 className="mt-3 font-serif text-5xl">The table isn&apos;t finished</h1>
        <p className="mt-4 text-ink-soft">
          {progress ? `${progress.finished} / ${progress.total} people finished` : "Waiting for every swipe."}
        </p>
        {error && !progress ? <p className="mt-2 text-sm text-ink-soft">{error}</p> : null}
      </section>
    );
  }

  const others = results?.alternatives.slice(0, 4) || [];

  return (
    <section className="mx-auto max-w-2xl pt-4">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <p className="text-sm uppercase tracking-[0.22em] text-chili">Group match</p>
        <article className="mt-4 overflow-hidden rounded-[32px] border border-line bg-card shadow-card">
          <div className="px-6 py-8 sm:px-10" style={{ background: cuisineWash(top.cuisine) }}>
            <p className="text-xs uppercase tracking-[0.18em]">{top.cuisine || "Restaurant"}</p>
            <h1 className="mt-3 font-serif text-5xl leading-none sm:text-6xl">{top.name}</h1>
          </div>
          <div className="space-y-4 px-6 py-8 sm:px-10">
            <p className="font-serif text-5xl text-moss">{top.compatibility_percent}%</p>
            <p className="text-lg">Group match</p>
            <p className="text-ink-soft">
              {top.likes} of {top.total_participants} people liked this restaurant.
            </p>
            {[formatPrice(top.price), formatRating(top.rating), top.address].filter(Boolean).length > 0 ? (
              <p className="text-sm text-ink-soft">
                {[formatPrice(top.price), formatRating(top.rating), top.address].filter(Boolean).join(" · ")}
              </p>
            ) : null}
            <button
              type="button"
              onClick={() => setShowWhy((value) => !value)}
              className="rounded-full border border-line px-4 py-2 text-sm"
            >
              Why this one?
            </button>
            {showWhy ? <p className="rounded-2xl bg-paper px-4 py-3 text-sm">{top.explanation}</p> : null}
          </div>
        </article>
      </motion.div>

      {others.length > 0 ? (
        <div className="mt-8">
          <h2 className="font-serif text-3xl">Other strong matches</h2>
          <ul className="mt-4 space-y-3">
            {others.map((restaurant) => (
              <li key={restaurant.restaurant_id} className="rounded-2xl border border-line bg-card px-4 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium">{restaurant.name}</p>
                    <p className="text-sm text-ink-soft">{restaurant.cuisine || "Restaurant"}</p>
                  </div>
                  <p className="font-serif text-2xl">{restaurant.compatibility_percent}%</p>
                </div>
                <div className="mt-3 h-2 rounded-full bg-paper-deep">
                  <div
                    className="h-2 rounded-full bg-moss"
                    style={{ width: `${restaurant.compatibility_percent}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
