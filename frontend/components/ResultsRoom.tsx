"use client";

import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { cuisineWash, formatPrice, formatRating } from "@/lib/format";
import { getResults, speakConcierge } from "@/lib/api";
import { afterSound, isSoundEnabled, playSoundOnce, playSpeech } from "@/lib/audio";
import { SATISFACTION_HINT, SATISFACTION_LABEL, describeResult, whyThisWon } from "@/lib/results";
import { useSession } from "@/lib/useSession";
import type { Results } from "@/types";

const SPEECH_LIMIT = 400;

export function ResultsRoom({ roomCode }: { roomCode: string }) {
  const router = useRouter();
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [whyAudio, setWhyAudio] = useState<"idle" | "loading" | "unavailable">("idle");
  const whyClip = useRef<{ text: string; clip: Blob } | null>(null);
  const { session, progress, eventName } = useSession(roomCode);
  const winnerId = results?.top_match?.restaurant_id;
  const winnerName = results?.top_match?.name;

  useEffect(() => {
    if (!winnerId || !winnerName) return;
    let cancelled = false;
    let cancelStep = afterSound("matching", () => {
      if (!playSoundOnce(`winner:${roomCode.toUpperCase()}`, "winner")) return;
      const announcement = isSoundEnabled()
        ? speakConcierge(`We have a winner. Your group is going to ${winnerName}.`)
        : Promise.resolve(null);
      cancelStep = afterSound("winner", () => {
        void announcement.then((clip) => {
          if (clip && !cancelled) void playSpeech(clip);
        });
      });
    });
    return () => {
      cancelled = true;
      cancelStep();
    };
  }, [roomCode, winnerId, winnerName]);

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

  const alternatives = results?.alternatives || [];
  const others = alternatives.filter((item, index) => index < 4 || item.highlight === "higher_satisfaction");
  const view = describeResult(top);
  const why = whyThisWon(top);

  async function hearWhy() {
    if (!top || whyAudio === "loading") return;
    setWhyAudio("loading");
    const text = speakable(`Why ${top.name}? ${why}`);
    let clip = whyClip.current?.text === text ? whyClip.current.clip : null;
    if (!clip) {
      clip = await speakConcierge(text);
      if (clip) whyClip.current = { text, clip };
    }
    const played = clip ? await playSpeech(clip, { force: true }) : false;
    setWhyAudio(played ? "idle" : "unavailable");
  }

  return (
    <section className="mx-auto max-w-2xl pt-4">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <p className="text-sm uppercase tracking-[0.22em] text-chili">Your group&apos;s pick</p>
        <article className="mt-4 overflow-hidden rounded-[32px] border border-line bg-card shadow-card">
          <div className="px-6 py-8 sm:px-10" style={{ background: cuisineWash(top.cuisine) }}>
            <p className="text-xs uppercase tracking-[0.18em]">{top.cuisine || "Restaurant"}</p>
            <h1 className="mt-3 font-serif text-5xl leading-none sm:text-6xl">{top.name}</h1>
          </div>
          <div className="space-y-4 px-6 py-8 sm:px-10">
            {view.badge ? (
              <span className="inline-block rounded-full bg-paper px-3 py-1 text-xs uppercase tracking-[0.14em] text-moss">
                {view.badge}
              </span>
            ) : null}
            {view.percent !== null ? (
              <div>
                <p className="text-lg" title={SATISFACTION_HINT}>
                  {SATISFACTION_LABEL}
                </p>
                <p className="font-serif text-5xl text-moss">{view.percent}%</p>
                <SatisfactionBar percent={view.percent} />
              </div>
            ) : null}
            {view.positiveLine ? (
              <p className="text-ink-soft">
                <span className="text-ink">{view.positiveLine}</span>
                {view.breakdown ? ` · ${view.breakdown}` : ""}
              </p>
            ) : null}
            {view.eligibility ? <p className="text-sm text-chili">{view.eligibility}</p> : null}
            {[formatPrice(top.price), formatRating(top.rating), top.address].filter(Boolean).length > 0 ? (
              <p className="text-sm text-ink-soft">
                {[formatPrice(top.price), formatRating(top.rating), top.address].filter(Boolean).join(" · ")}
              </p>
            ) : null}
            <div className="border-t border-line pt-4">
              <h2 className="font-serif text-2xl">Why this won</h2>
              <p className="mt-2 text-ink-soft">{why}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => void hearWhy()}
                disabled={whyAudio === "loading"}
                className="rounded-full border border-line px-4 py-2 text-sm disabled:opacity-60"
              >
                <span aria-hidden="true">🔊</span> {whyAudio === "loading" ? "Getting audio..." : "Hear why"}
              </button>
              {whyAudio === "unavailable" ? <span className="text-xs text-ink-soft">Audio unavailable</span> : null}
            </div>
          </div>
        </article>
      </motion.div>

      {others.length > 0 ? (
        <div className="mt-8">
          <h2 className="font-serif text-3xl">Other options</h2>
          <p className="mt-1 text-sm text-ink-soft">
            Percentages are {SATISFACTION_LABEL.toLowerCase()}. Nomly ranks by fairness first, so the highest number
            does not always win.
          </p>
          <ul className="mt-4 space-y-3">
            {others.map((restaurant) => {
              const item = describeResult(restaurant);
              return (
                <li
                  key={restaurant.restaurant_id}
                  className={`rounded-2xl border border-line bg-card px-4 py-4 ${item.eligibility ? "opacity-70" : ""}`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-medium">{restaurant.name}</p>
                      <p className="text-sm text-ink-soft">{restaurant.cuisine || "Restaurant"}</p>
                    </div>
                    {item.percent !== null ? (
                      <div className="text-right">
                        <p className="font-serif text-2xl">{item.percent}%</p>
                        <p className="text-xs text-ink-soft">satisfaction</p>
                      </div>
                    ) : null}
                  </div>
                  {item.percent !== null ? <SatisfactionBar percent={item.percent} muted={Boolean(item.eligibility)} /> : null}
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-soft">
                    {item.positiveLine ? (
                      <span>
                        {item.positiveLine}
                        {item.breakdown ? ` · ${item.breakdown}` : ""}
                      </span>
                    ) : null}
                    {item.badge ? (
                      <span className="rounded-full bg-paper px-2 py-0.5 text-xs uppercase tracking-[0.12em] text-gold">
                        {item.badge}
                      </span>
                    ) : null}
                    {item.eligibility ? <span className="text-chili">{item.eligibility}</span> : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function SatisfactionBar({ percent, muted = false }: { percent: number; muted?: boolean }) {
  return (
    <div
      className="mt-3 h-2 rounded-full bg-paper-deep"
      role="progressbar"
      aria-label={SATISFACTION_LABEL}
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className={`h-2 rounded-full ${muted ? "bg-ink-soft" : "bg-moss"}`} style={{ width: `${percent}%` }} />
    </div>
  );
}

function speakable(text: string) {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= SPEECH_LIMIT) return clean;
  const clipped = clean.slice(0, SPEECH_LIMIT);
  const end = clipped.lastIndexOf(". ");
  return end > 0 ? clipped.slice(0, end + 1) : clipped;
}
