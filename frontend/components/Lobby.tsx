"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { joinSession, startSession } from "@/lib/api";
import { preloadSounds } from "@/lib/audio";
import { loadIdentity, saveIdentity } from "@/lib/storage";
import { useRoomSounds } from "@/lib/useRoomSounds";
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
  const onRoomEvent = useRoomSounds(roomCode);
  const { session } = useSession(roomCode, identity?.participantId, onRoomEvent);

  useEffect(() => {
    setIdentity(loadIdentity(roomCode));
    setReady(true);
    preloadSounds(["join"]);
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

  if (!ready) return <p className="pt-16 text-center text-ink-soft">Opening the room...</p>;

  const isHost = Boolean(session && identity && session.host_participant_id === identity.participantId);
  const code = roomCode.toUpperCase();

  // Light border box, same as the other pages.
  const box = "rounded-2xl border border-ink/15 bg-card";
  const field = `${box} w-full px-4 py-3 text-lg outline-none placeholder:text-ink/40 transition-colors focus:border-[#2f4a22]/60 focus:bg-[#fffaf3] focus:ring-2 focus:ring-[#b5c384]`;
    const pill =
    "mt-5 h-12 w-full rounded-2xl bg-[#b5c384] text-lg text-[#1f3315] transition duration-100 enabled:hover:bg-[#a9b975] enabled:active:scale-[0.98] disabled:opacity-60";
    
  return (
    <section className="mx-auto w-full max-w-[360px] pt-6 font-serif">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-lg">Room</p>
          <h1 className="text-5xl leading-none">{code}</h1>
          <button
            type="button"
            onClick={() => void copyCode()}
            className="mt-2 text-sm text-ink-soft underline underline-offset-4"
          >
            {copied ? "Copied" : "Copy code"}
          </button>
        </div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/assets/chef_hat.webp" alt="" className="w-24" />
      </div>

      {!identity ? (
        <form onSubmit={onJoin} className="mt-6">
          <h2 className="text-center text-2xl">Join this dinner</h2>
          <input
            required
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            placeholder="Name"
            className={`mt-5 ${field}`}
          />
          {error ? <p className="mt-3 text-sm text-[#c45a56]">{error}</p> : null}
          <button type="submit" disabled={pending} className={pill}>
            {pending ? "Joining..." : "Join room"}
          </button>
        </form>
      ) : (
        <div className="mt-6">
          <h2 className="text-center text-2xl">Who&apos;s late?</h2>
          <ul className="mt-5 space-y-2">
            {(session?.participants || []).map((person) => (
              <li
                key={person.id}
                className={`${box} flex items-center justify-between px-4 py-2 text-lg ${
                  person.is_host ? "!bg-[#fffaf3]" : ""
                }`}
              >
                <span>{person.nickname}</span>
                {person.is_host ? <span className="text-xs uppercase tracking-[0.16em] text-ink-soft">Host</span> : null}
              </li>
            ))}
          </ul>
          {error ? <p className="mt-3 text-sm text-[#c45a56]">{error}</p> : null}
          {isHost ? (
            <button
              type="button"
              onClick={() => void onStart()}
              disabled={pending || !session}
              className="button-orange mt-6 w-full rounded-full px-5 py-3 disabled:opacity-60"
            >
              {pending ? "Starting..." : "Start dinner"}
            </button>
          ) : (
            <button type="button" disabled className={pill}>
              Waiting for the host...
            </button>
          )}
        </div>
      )}
    </section>
  );
}