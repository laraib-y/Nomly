"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { VoiceInput } from "@/components/VoiceInput";
import { createSession } from "@/lib/api";
import { saveIdentity } from "@/lib/storage";

export default function CreatePage() {
  const router = useRouter();
  const [description, setDescription] = useState("");
  const [nickname, setNickname] = useState("");
  const [location, setLocation] = useState("");
  const [groupSize, setGroupSize] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [spoken, setSpoken] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const session = await createSession({
        description,
        nickname,
        location,
        group_size: Number(groupSize),
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
            placeholder="Enter Your Name"
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
            placeholder="Describe your dinner preferences"
            className="form-field mt-2"
          />
          {spoken ? <p className="mt-2 text-sm text-ink-soft">You said this. Edit it if anything is off.</p> : null}
        </label>
        <VoiceInput
          onTranscript={(transcript) => {
            setDescription(transcript);
            setSpoken(true);
            setError(null);
          }}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-lg">
            <span>Group size</span>
            <input
              type="number"
              required
              min={1}
              max={20}
              value={groupSize}
              onChange={(event) => setGroupSize(event.target.value)}
              placeholder="Number of people"
              className="form-field mt-2"
            />
          </label>
          <label className="block text-lg">
            <span>Location</span>
            <input
              required
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              placeholder="Enter a city or neighborhood"
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
          {pending ? "Finding restaurants..." : spoken ? "Find dinner" : "Create dinner"}
        </button>
      </form>
    </section>
  );
}
