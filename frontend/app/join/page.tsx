"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { joinSession } from "@/lib/api";
import { saveIdentity } from "@/lib/storage";

export default function JoinPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const joined = await joinSession(code.trim().toLowerCase(), nickname);
      const participant = joined.participant;
      if (!participant) throw new Error("Join did not return a participant");
      saveIdentity(joined.room_code, { participantId: participant.id, nickname: participant.nickname });
      router.push(`/dinner/${joined.room_code}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join");
      setPending(false);
    }
  }

  return (
    <section className="mx-auto w-full max-w-[600px] px-4 pt-10 font-serif">
      <h1 className="text-center text-5xl leading-tight">Got the code?</h1>

      <form onSubmit={onSubmit} className="form-panel mt-10 p-6 sm:p-8">
        <label htmlFor="room-code" className="block text-lg">
          Room code
        </label>
        <input
          id="room-code"
          required
          autoComplete="off"
          autoCapitalize="characters"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          className="form-field mt-2 uppercase tracking-[0.2em]"
        />

        <label htmlFor="nickname" className="mt-5 block text-lg">
          Name
        </label>
        <input
          id="nickname"
          required
          autoComplete="off"
          value={nickname}
          onChange={(event) => setNickname(event.target.value)}
          className="form-field mt-2"
        />

        {error ? <p className="form-error mt-4 text-sm">{error}</p> : null}

        <button
          type="submit"
          disabled={pending}
          className="button-primary mt-5 h-12 w-full rounded-2xl text-lg disabled:opacity-60"
        >
          {pending ? "Joining..." : "Join your friends!"}
        </button>
      </form>
    </section>
  );
}