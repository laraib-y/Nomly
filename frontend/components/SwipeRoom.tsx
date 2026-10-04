"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { DecisionButtons, RestaurantCard } from "@/components/RestaurantCard";
import { getRestaurants, sendSwipe } from "@/lib/api";
import { loadIdentity } from "@/lib/storage";
import { useSession } from "@/lib/useSession";
import type { Identity, Progress, Restaurant } from "@/types";

export function SwipeRoom({ roomCode }: { roomCode: string }) {
  const router = useRouter();
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [restaurants, setRestaurants] = useState<Restaurant[] | null>(null);
  const [cursor, setCursor] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [localProgress, setLocalProgress] = useState<Progress | null>(null);
  const direction = useRef<"like" | "pass">("like");
  const { session, progress, eventName } = useSession(roomCode, identity?.participantId);

  useEffect(() => {
    const stored = loadIdentity(roomCode);
    setIdentity(stored);
    if (!stored) router.replace(`/dinner/${roomCode}`);
  }, [roomCode, router]);

  useEffect(() => {
    if (!identity) return;
    let cancelled = false;
    getRestaurants(roomCode, identity.participantId)
      .then((deck) => {
        if (cancelled) return;
        setRestaurants(deck);
        const next = deck.findIndex((restaurant) => !restaurant.my_decision);
        setCursor(next === -1 ? deck.length : next);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load restaurants");
      });
    return () => {
      cancelled = true;
    };
  }, [identity, roomCode]);

  useEffect(() => {
    if (session?.status === "lobby") router.replace(`/dinner/${roomCode}`);
    if (session?.status === "completed" || eventName === "results_ready" || eventName === "all_completed") {
      router.push(`/dinner/${roomCode}/results`);
    }
  }, [eventName, roomCode, router, session]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "ArrowLeft") void choose("pass");
      if (event.key === "ArrowRight") void choose("like");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const current = restaurants?.[cursor];
  const done = Boolean(restaurants && cursor >= restaurants.length);
  const shownProgress = localProgress || progress;

  async function choose(decision: "like" | "pass") {
    if (!identity || !current || pending || done) return;
    direction.current = decision;
    setPending(true);
    setError(null);
    try {
      const result = await sendSwipe(roomCode, identity.participantId, current.id, decision);
      setLocalProgress(result.progress);
      if (result.all_completed) {
        router.push(`/dinner/${roomCode}/results`);
        return;
      }
      setCursor((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that swipe");
    } finally {
      setPending(false);
    }
  }

  if (!restaurants) {
    return <p className="pt-16 text-ink-soft">{error || "Setting the table..."}</p>;
  }

  return (
    <section className="mx-auto max-w-md pt-2">
      <div className="mb-4 flex items-center justify-between text-sm text-ink-soft">
        <span>
          {Math.min(cursor + (done ? 0 : 1), restaurants.length)} / {restaurants.length}
        </span>
        <span>{shownProgress ? `${shownProgress.finished} / ${shownProgress.total} people finished` : "Swipe privately"}</span>
      </div>

      {done ? (
        <div className="rounded-[28px] border border-line bg-card p-8 text-center shadow-card">
          <p className="text-xs uppercase tracking-[0.18em] text-moss">You&apos;re done</p>
          <h1 className="mt-3 font-serif text-4xl">Waiting on the table</h1>
          <p className="mt-3 text-ink-soft">
            {shownProgress
              ? `${shownProgress.finished} / ${shownProgress.total} people finished`
              : "Choices stay private until everyone is done."}
          </p>
        </div>
      ) : (
        <AnimatePresence mode="wait">
          {current ? (
            <motion.div
              key={current.id}
              initial={{ opacity: 0, y: 18, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{
                opacity: 0,
                x: direction.current === "like" ? 220 : -220,
                rotate: direction.current === "like" ? 8 : -8,
              }}
              transition={{ type: "spring", stiffness: 340, damping: 28 }}
              drag="x"
              dragConstraints={{ left: 0, right: 0 }}
              onDragEnd={(_, info) => {
                if (info.offset.x > 110) void choose("like");
                if (info.offset.x < -110) void choose("pass");
              }}
            >
              <RestaurantCard restaurant={current} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      )}

      {!done ? <DecisionButtons disabled={pending} onPass={() => void choose("pass")} onLike={() => void choose("like")} /> : null}
      {error ? <p className="mt-4 text-center text-sm text-chili">{error}</p> : null}
      <p className="mt-4 text-center text-xs text-ink-soft">Arrow keys work too. Left to pass, right to like.</p>
    </section>
  );
}
