import type { DinnerSession, Restaurant, Results, SwipeResult } from "@/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Can't reach the Nomly API. Start the backend on port 8000.");
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) {
        detail = body.detail.map((item: { msg?: string }) => item.msg || "Invalid request").join(" ");
      }
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, detail || "Request failed");
  }

  return response.json() as Promise<T>;
}

export async function transcribeAudio(audio: Blob): Promise<string> {
  const body = new FormData();
  const type = audio.type || "audio/webm";
  body.append("audio", audio, type.includes("wav") ? "dinner.wav" : "dinner.webm");
  const payload = await voiceRequest<{ transcript: string }>("/api/voice/transcribe", { method: "POST", body });
  return payload.transcript;
}

export async function speakConcierge(text: string): Promise<Blob | null> {
  try {
    const response = await fetch(`${API_URL}/api/voice/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.slice(0, 400) }),
    });
    if (!response.ok) return null;
    return await response.blob();
  } catch {
    return null;
  }
}

async function voiceRequest<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
  } catch {
    throw new ApiError(0, "Can't reach the Nomly API. Start the backend on port 8000.");
  }
  if (!response.ok) {
    let detail = "Voice is temporarily unavailable. You can type your dinner plans instead.";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      detail = "We couldn't understand that recording. Try again or type your dinner plans instead.";
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export function createSession(input: {
  description: string;
  nickname: string;
  location: string;
  group_size: number;
}) {
  return request<DinnerSession>("/api/sessions", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function joinSession(roomCode: string, nickname: string) {
  return request<DinnerSession>(`/api/sessions/${encodeURIComponent(roomCode)}/join`, {
    method: "POST",
    body: JSON.stringify({ nickname }),
  });
}

export function getSession(roomCode: string) {
  return request<DinnerSession>(`/api/sessions/${encodeURIComponent(roomCode)}`);
}

export function startSession(roomCode: string, participantId: string) {
  return request<DinnerSession>(`/api/sessions/${encodeURIComponent(roomCode)}/start`, {
    method: "POST",
    body: JSON.stringify({ participant_id: participantId }),
  });
}

export function getRestaurants(roomCode: string, participantId: string) {
  const params = new URLSearchParams({ participant_id: participantId });
  return request<Restaurant[]>(`/api/sessions/${encodeURIComponent(roomCode)}/restaurants?${params}`);
}

export function sendSwipe(
  roomCode: string,
  participantId: string,
  restaurantId: string,
  decision: "like" | "pass" | "super_like" | "veto",
) {
  return request<SwipeResult>(`/api/sessions/${encodeURIComponent(roomCode)}/swipes`, {
    method: "POST",
    body: JSON.stringify({
      participant_id: participantId,
      restaurant_id: restaurantId,
      decision,
    }),
  });
}

export function getResults(roomCode: string) {
  return request<Results>(`/api/sessions/${encodeURIComponent(roomCode)}/results`);
}

export function sessionSocketUrl(roomCode: string, participantId?: string) {
  const code = roomCode.trim().toUpperCase();
  const url = new URL(API_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/sessions/${code}`;
  url.search = "";
  url.hash = "";
  if (participantId) url.searchParams.set("participant_id", participantId);
  return url.toString();
}
