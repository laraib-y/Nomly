"use client";

import { useEffect, useRef, useState } from "react";

import { getSession, sessionSocketUrl } from "@/lib/api";
import type { DinnerSession, LiveEvent, Progress } from "@/types";

const MAX_SOCKET_RETRIES = 8;

export function useSession(roomCode: string, participantId?: string, onEvent?: (event: LiveEvent) => void) {
  const [session, setSession] = useState<DinnerSession | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [eventName, setEventName] = useState<string | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    const code = roomCode.trim().toUpperCase();
    if (!code) return;

    let cancelled = false;
    let socket: WebSocket | null = null;
    let retry = 0;
    let retryTimer = 0;

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

    function connect() {
      if (cancelled) return;
      const next = new WebSocket(sessionSocketUrl(code, participantId));
      socket = next;

      next.onopen = () => {
        if (cancelled || socket !== next) {
          if (next.readyState === WebSocket.OPEN) next.close();
          return;
        }
        retry = 0;
        setConnected(true);
      };
      next.onerror = () => {
        if (socket === next) setConnected(false);
      };
      next.onclose = (event) => {
        if (socket !== next) return;
        setConnected(false);
        if (cancelled || event.code === 1008 || retry >= MAX_SOCKET_RETRIES) return;
        const delay = Math.min(500 * 2 ** retry, 5000);
        retry += 1;
        retryTimer = window.setTimeout(connect, delay);
      };
      next.onmessage = (message) => {
        if (cancelled || socket !== next) return;
        let event: LiveEvent;
        try {
          event = JSON.parse(message.data) as LiveEvent;
        } catch {
          return;
        }
        setEventName(event.type);
        try {
          onEventRef.current?.(event);
        } catch {
          // Listeners add polish only. They must not stop room updates.
        }
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
    }

    void reload();
    const poll = window.setInterval(() => void reload(), 4000);
    // Wait one turn so a Strict Mode remount can cancel before the handshake starts.
    const startTimer = window.setTimeout(connect, 0);

    return () => {
      cancelled = true;
      window.clearInterval(poll);
      window.clearTimeout(startTimer);
      window.clearTimeout(retryTimer);
      const current = socket;
      socket = null;
      if (!current) return;
      if (current.readyState === WebSocket.OPEN) current.close();
      else if (current.readyState === WebSocket.CONNECTING) {
        current.addEventListener(
          "open",
          () => {
            current.close();
          },
          { once: true },
        );
      }
    };
  }, [roomCode, participantId]);

  return { session, progress, error, connected, eventName };
}
