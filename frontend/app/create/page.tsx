"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { createSession } from "@/lib/api";
import { saveIdentity } from "@/lib/storage";

export default function CreatePage() {
  const router = useRouter();
  const [description, setDescription] = useState(
    "We want something casual, Japanese or Korean, under $30 per person, around Burnaby.",
  );
  const [nickname, setNickname] = useState("");
  const [location, setLocation] = useState("Burnaby");
  const [groupSize, setGroupSize] = useState(5);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const session = await createSession({
        description,
        nickname,
        location,
        group_size: groupSize,
      });
      const participant = session.participant;
      if (!participant) throw new Error("The room was created without a host");
      saveIdentity(session.room_code, { participantId: participant.id, nickname: participant.nickname });
      router.push(`/dinner/${session.room_code}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create dinner");
      setPending(false);
    }
  }

  return (
    <section className="mx-auto max-w-2xl pt-6">
      <p className="text-sm uppercase tracking-[0.2em] text-chili">Create dinner</p>
      <h1 className="mt-3 font-serif text-5xl">What are you looking for?</h1>
      <form onSubmit={onSubmit} className="mt-8 space-y-5 rounded-[28px] border border-line bg-card p-6 shadow-card">
        <label className="block">
          <span className="text-sm text-ink-soft">Your name</span>
          <input
            required
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            placeholder="Abdalla"
            className="mt-2 w-full rounded-2xl border border-line bg-paper px-4 py-3 outline-none focus:border-chili"
          />
        </label>
        <label className="block">
          <span className="text-sm text-ink-soft">Dinner notes</span>
          <textarea
            required
            minLength={3}
            rows={5}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="mt-2 w-full rounded-2xl border border-line bg-paper px-4 py-3 outline-none focus:border-chili"
          />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm text-ink-soft">Group size</span>
            <input
              type="number"
              min={1}
              max={20}
              value={groupSize}
              onChange={(event) => setGroupSize(Number(event.target.value))}
              className="mt-2 w-full rounded-2xl border border-line bg-paper px-4 py-3 outline-none focus:border-chili"
            />
          </label>
          <label className="block">
            <span className="text-sm text-ink-soft">Location</span>
            <input
              required
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-line bg-paper px-4 py-3 outline-none focus:border-chili"
            />
          </label>
        </div>
        {error ? <p className="text-sm text-chili">{error}</p> : null}
        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-full bg-chili px-5 py-3 text-white disabled:opacity-60"
        >
          {pending ? "Finding restaurants..." : "Create dinner"}
        </button>
        <p className="text-sm text-ink-soft">
          Anyone with the room code can join. You can start when the group is here.
        </p>
      </form>
    </section>
  );
}
