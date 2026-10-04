"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ResultsDisplay } from "@/components/ResultsDisplay";
import { getResults, speakConcierge } from "@/lib/api";
import { afterSound, isSoundEnabled, playSoundOnce, playSpeech } from "@/lib/audio";
import { whyThisWon } from "@/lib/results";
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
  if (!results || !top) {
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
      <ResultsDisplay
        results={results}
        whyActions={
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
        }
      />
    </section>
  );
}

function speakable(text: string) {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= SPEECH_LIMIT) return clean;
  const clipped = clean.slice(0, SPEECH_LIMIT);
  const end = clipped.lastIndexOf(". ");
  return end > 0 ? clipped.slice(0, end + 1) : clipped;
}
