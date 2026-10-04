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
    <section className="mx-auto w-full max-w-[600px] px-4 pt-10 font-serif">
      <h1 className="text-center text-5xl leading-tight">What are you looking for?</h1>
      <form onSubmit={onSubmit} className="form-panel mt-10 space-y-5 p-6 sm:p-8">
        <label className="block text-lg">
          <span>Your name</span>
          <input
            required
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            placeholder="Abdalla"
            className="form-field mt-2"
          />
        </label>
        <label className="block text-lg">
          <span>Describe the night</span>
          <p className="mt-1 text-sm text-ink-soft">
            Plain language is enough. Location and group size below are used as you type them.
          </p>
          <textarea
            required
            minLength={3}
            rows={5}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="form-field mt-2"
          />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-lg">
            <span>Group size</span>
            <input
              type="number"
              min={1}
              max={20}
              value={groupSize}
              onChange={(event) => setGroupSize(Number(event.target.value))}
              className="form-field mt-2"
            />
          </label>
          <label className="block text-lg">
            <span>Location</span>
            <input
              required
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              className="form-field mt-2"
            />
          </label>
        </div>
        {error ? <p className="form-error text-sm">{error}</p> : null}
        <button
          type="submit"
          disabled={pending}
          className="button-primary w-full rounded-2xl py-3 text-lg disabled:opacity-60"
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
