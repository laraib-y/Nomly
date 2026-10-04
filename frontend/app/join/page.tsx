"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { joinSession } from "@/lib/api";
import { saveIdentity } from "@/lib/storage";

const panel = "rounded-3xl border border-ink/10 bg-[#fbf8f2]";
const box = "rounded-2xl border border-ink/15 bg-card";
const fieldInput = `${box} w-full px-4 py-3 text-lg outline-none placeholder:text-ink/40 transition-colors focus:border-[#2f4a22]/60 focus:bg-[#fffaf3] focus:ring-2 focus:ring-[#b5c384]`;
const pill =
  "mt-5 h-12 w-full rounded-2xl bg-[#b5c384] text-lg text-[#1f3315] transition duration-100 enabled:hover:bg-[#a9b975] enabled:active:scale-[0.98] disabled:opacity-60";

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

      <form onSubmit={onSubmit} className={`${panel} mt-10 p-6 sm:p-8`}>
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
          className={`mt-2 uppercase tracking-[0.2em] ${fieldInput}`}
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
          className={`mt-2 ${fieldInput}`}
        />

        {error ? <p className="mt-4 text-sm text-[#c45a56]">{error}</p> : null}

        <button type="submit" disabled={pending} className={pill}>
          {pending ? "Joining..." : "Join your friends!"}
        </button>
      </form>
    </section>
  );
}