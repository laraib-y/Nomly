"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { joinSession, startSession } from "@/lib/api";
import { loadIdentity, saveIdentity } from "@/lib/storage";
import { useSession } from "@/lib/useSession";
import type { Identity } from "@/types";

export function Lobby({ roomCode }: { roomCode: string }) {
  const router = useRouter();
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [ready, setReady] = useState(false);
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [copied, setCopied] = useState(false);
  const { session } = useSession(roomCode, identity?.participantId);

  useEffect(() => {
    setIdentity(loadIdentity(roomCode));
    setReady(true);
  }, [roomCode]);

  useEffect(() => {
    if (!session) return;
    if (session.status === "active") router.push(`/dinner/${session.room_code}/swipe`);
    if (session.status === "completed") router.push(`/dinner/${session.room_code}/results`);
  }, [router, session]);

  async function onJoin(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const joined = await joinSession(roomCode, nickname);
      const participant = joined.participant;
      if (!participant) throw new Error("Join did not return a participant");
      const next = { participantId: participant.id, nickname: participant.nickname };
      saveIdentity(joined.room_code, next);
      setIdentity(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join");
    } finally {
      setPending(false);
    }
  }

  async function onStart() {
    if (!identity) return;
    setPending(true);
    setError(null);
    try {
      await startSession(roomCode, identity.participantId);
      router.push(`/dinner/${roomCode}/swipe`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start dinner");
      setPending(false);
    }
  }

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(roomCode.toUpperCase());
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setError("Could not copy the room code");
    }
  }

  if (!ready) return <p className="pt-16 text-ink-soft">Opening the room...</p>;

  const isHost = Boolean(session && identity && session.host_participant_id === identity.participantId);

  return (
    <section className="mx-auto max-w-xl pt-4">
      <p className="text-sm uppercase tracking-[0.2em] text-chili">DineOff</p>
      <div className="mt-3 flex items-end justify-between gap-4">
        <div>
          <p className="text-sm text-ink-soft">Room</p>
          <h1 className="font-serif text-6xl tracking-[0.12em]">{roomCode.toUpperCase()}</h1>
        </div>
        <button type="button" onClick={() => void copyCode()} className="rounded-full border border-line bg-card px-4 py-2 text-sm">
          {copied ? "Copied" : "Copy code"}
        </button>
      </div>

      {!identity ? (
        <form onSubmit={onJoin} className="mt-8 space-y-4 rounded-[28px] border border-line bg-card p-6">
          <h2 className="font-serif text-3xl">Join this dinner</h2>
          <input
            required
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            placeholder="Your name"
            className="w-full rounded-2xl border border-line bg-paper px-4 py-3 outline-none focus:border-chili"
          />
          {error ? <p className="text-sm text-chili">{error}</p> : null}
          <button type="submit" disabled={pending} className="w-full rounded-full bg-ink px-5 py-3 text-paper">
            {pending ? "Joining..." : "Join room"}
          </button>
        </form>
      ) : (
        <div className="mt-8 rounded-[28px] border border-line bg-card p-6 shadow-card">
          <h2 className="font-serif text-3xl">Who&apos;s coming?</h2>
          <ul className="mt-5 space-y-3">
            {(session?.participants || []).map((person) => (
              <li key={person.id} className="flex items-center justify-between rounded-2xl bg-paper px-4 py-3">
                <span>{person.nickname}</span>
                {person.is_host ? <span className="text-xs uppercase tracking-[0.16em] text-gold">Host</span> : null}
              </li>
            ))}
          </ul>
          {error ? <p className="mt-5 text-sm text-chili">{error}</p> : null}
          {isHost ? (
            <button
              type="button"
              onClick={() => void onStart()}
              disabled={pending || !session}
              className="mt-6 w-full rounded-full bg-chili px-5 py-3 text-white disabled:opacity-60"
            >
              {pending ? "Starting..." : "Start dinner"}
            </button>
          ) : (
            <p className="mt-6 text-center text-ink-soft">Waiting for the host...</p>
          )}
        </div>
      )}
    </section>
  );
}
