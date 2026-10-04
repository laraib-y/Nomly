"use client";

import { useEffect, useState } from "react";

import { getSession, sessionSocketUrl } from "@/lib/api";
import type { DinnerSession, LiveEvent, Progress } from "@/types";

export function useSession(roomCode: string, participantId?: string) {
  const [session, setSession] = useState<DinnerSession | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [eventName, setEventName] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const code = roomCode.trim().toUpperCase();

    async function reload() {
      try {
        const next = await getSession(code);
        if (cancelled) return;
        setSession(next);
        setProgress(next.progress);
        setError(null);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load this dinner");
      }
    }

    void reload();
    const poll = window.setInterval(() => void reload(), 4000);
    const socket = new WebSocket(sessionSocketUrl(code, participantId));

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);
    socket.onmessage = (message) => {
      let event: LiveEvent;
      try {
        event = JSON.parse(message.data) as LiveEvent;
      } catch {
        return;
      }
      setEventName(event.type);
      if (event.type === "swipe_progress" || event.type === "all_completed") {
        if (typeof event.finished === "number" && typeof event.total === "number") {
          setProgress({ finished: event.finished, total: event.total });
        }
      }
      if (event.type === "state" && event.finished != null && event.total != null) {
        setProgress({ finished: event.finished, total: event.total });
      }
      if (["state", "participant_joined", "participant_left", "dinner_started", "results_ready"].includes(event.type)) {
        void reload();
      }
    };

    return () => {
      cancelled = true;
      window.clearInterval(poll);
      socket.close();
    };
  }, [roomCode, participantId]);

  return { session, progress, error, connected, eventName };
}
