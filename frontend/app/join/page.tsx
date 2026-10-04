"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { joinSession } from "@/lib/api";
import { saveIdentity } from "@/lib/storage";

export default function JoinPage() {
  const router = useRouter();
  const [roomCode, setRoomCode] = useState("");
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const session = await joinSession(roomCode, nickname);
      const participant = session.participant;
      if (!participant) throw new Error("Join did not return a participant");
      saveIdentity(session.room_code, { participantId: participant.id, nickname: participant.nickname });
      router.push(`/dinner/${session.room_code}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join");
      setPending(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl pt-8">
      <p className="text-sm uppercase tracking-[0.2em] text-chili">Join dinner</p>
      <h1 className="mt-3 font-serif text-5xl">Got a room code?</h1>
      <form onSubmit={onSubmit} className="mt-8 space-y-5 rounded-[28px] border border-line bg-card p-6 shadow-card">
        <label className="block">
          <span className="text-sm text-ink-soft">Room code</span>
          <input
            required
            value={roomCode}
            onChange={(event) => setRoomCode(event.target.value.toUpperCase())}
            placeholder="AB7KQ2"
            className="mt-2 w-full rounded-2xl border border-line bg-paper px-4 py-3 font-serif text-2xl tracking-[0.2em] outline-none focus:border-chili"
          />
        </label>
        <label className="block">
          <span className="text-sm text-ink-soft">Your name</span>
          <input
            required
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            placeholder="Sarah"
            className="mt-2 w-full rounded-2xl border border-line bg-paper px-4 py-3 outline-none focus:border-chili"
          />
        </label>
        {error ? <p className="text-sm text-chili">{error}</p> : null}
        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-full bg-ink px-5 py-3 text-paper disabled:opacity-60"
        >
          {pending ? "Joining..." : "Join dinner"}
        </button>
      </form>
    </section>
  );
}
