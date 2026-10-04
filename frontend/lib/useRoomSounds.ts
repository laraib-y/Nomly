"use client";

import { useCallback, useRef } from "react";

import { playSoundOnce, soundForRoomEvent } from "@/lib/audio";
import type { LiveEvent } from "@/types";

/** Turns existing room events into sounds. Pass the result to useSession. */
export function useRoomSounds(roomCode: string) {
  const lastFinished = useRef<number | null>(null);

  return useCallback(
    (event: LiveEvent) => {
      const cue = soundForRoomEvent(roomCode, event, lastFinished.current);
      if (cue) playSoundOnce(cue.key, cue.sound);
      if (typeof event.finished === "number") {
        lastFinished.current = Math.max(lastFinished.current ?? 0, event.finished);
      }
    },
    [roomCode],
  );
}
