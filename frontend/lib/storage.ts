import type { Identity } from "@/types";

function key(roomCode: string) {
  return `dineoff:${roomCode.trim().toUpperCase()}`;
}

export function saveIdentity(roomCode: string, identity: Identity) {
  window.sessionStorage.setItem(key(roomCode), JSON.stringify(identity));
}

export function loadIdentity(roomCode: string): Identity | null {
  const raw = window.sessionStorage.getItem(key(roomCode));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Identity;
    if (!parsed.participantId || !parsed.nickname) return null;
    return parsed;
  } catch {
    return null;
  }
}
