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
    throw new ApiError(0, "Can't reach the DineOff API. Start the backend on port 8000.");
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

export function sendSwipe(roomCode: string, participantId: string, restaurantId: string, decision: "like" | "pass") {
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
  const base = API_URL.replace(/^http/, "ws");
  const query = participantId ? `?participant_id=${encodeURIComponent(participantId)}` : "";
  return `${base}/ws/sessions/${encodeURIComponent(roomCode.trim().toUpperCase())}${query}`;
}
