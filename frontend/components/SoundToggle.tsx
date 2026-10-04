"use client";

import { useSyncExternalStore } from "react";

import { isSoundEnabled, setSoundEnabled, subscribeSound } from "@/lib/audio";

export function SoundToggle() {
  const enabled = useSyncExternalStore(subscribeSound, isSoundEnabled, () => true);

  return (
    <button
      type="button"
      onClick={() => setSoundEnabled(!enabled)}
      aria-pressed={enabled}
      aria-label={enabled ? "Turn sound off" : "Turn sound on"}
      className="rounded-full px-3 py-2 text-ink-soft hover:text-ink"
    >
      <span aria-hidden="true">{enabled ? "🔊" : "🔇"}</span>
      <span className="ml-1 hidden sm:inline">{enabled ? "Sound on" : "Sound off"}</span>
    </button>
  );
}
