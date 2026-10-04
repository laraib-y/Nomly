export type SoundName =
  | "like"
  | "pass"
  | "superlike"
  | "veto"
  | "join"
  | "participant-finished"
  | "matching"
  | "winner";

type Decision = "like" | "pass" | "super_like" | "veto";

type RoomEvent = {
  type: string;
  finished?: number;
  total?: number;
  participant?: { id: string };
};

const SOUNDS: Record<SoundName, { src: string; volume: number }> = {
  like: { src: "/audio/swipes/like.mp3", volume: 0.5 },
  pass: { src: "/audio/swipes/pass.mp3", volume: 0.4 },
  superlike: { src: "/audio/swipes/superlike.mp3", volume: 0.6 },
  veto: { src: "/audio/swipes/veto.mp3", volume: 0.55 },
  join: { src: "/audio/multiplayer/join.mp3", volume: 0.45 },
  "participant-finished": { src: "/audio/multiplayer/participant-finished.mp3", volume: 0.45 },
  matching: { src: "/audio/matching/matching.mp3", volume: 0.55 },
  winner: { src: "/audio/matching/winner.mp3", volume: 0.7 },
};

const STORAGE_KEY = "nomly:sound";
const MAX_WAIT_MS = 2500;

const loaded = new Map<SoundName, HTMLAudioElement>();
const playing = new Map<SoundName, HTMLAudioElement>();
const usedKeys = new Set<string>();
const listeners = new Set<() => void>();
let speech: HTMLAudioElement | null = null;

export function soundForDecision(decision: Decision): SoundName {
  return decision === "super_like" ? "superlike" : decision;
}

/**
 * Maps a live room event to a sound, keyed so each moment plays once even if
 * the same event arrives twice or a component remounts.
 */
export function soundForRoomEvent(
  roomCode: string,
  event: RoomEvent,
  lastFinished: number | null,
): { sound: SoundName; key: string } | null {
  const code = roomCode.toUpperCase();
  if (event.type === "participant_joined" && event.participant?.id) {
    return { sound: "join", key: `join:${code}:${event.participant.id}` };
  }
  if (event.type === "all_completed") {
    return { sound: "matching", key: `matching:${code}` };
  }
  if (
    event.type === "swipe_progress" &&
    lastFinished !== null &&
    typeof event.finished === "number" &&
    typeof event.total === "number" &&
    event.finished > lastFinished &&
    event.finished < event.total
  ) {
    return { sound: "participant-finished", key: `finished:${code}:${event.finished}` };
  }
  return null;
}

/** Returns true the first time a key is seen in this page session. */
export function once(key: string): boolean {
  if (usedKeys.has(key)) return false;
  usedKeys.add(key);
  return true;
}

export function isSoundEnabled(): boolean {
  try {
    return globalThis.localStorage?.getItem(STORAGE_KEY) !== "off";
  } catch {
    return true;
  }
}

export function setSoundEnabled(enabled: boolean): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, enabled ? "on" : "off");
  } catch {
    // Private mode can block storage. The toggle still works for this page.
  }
  if (!enabled) stopAll();
  listeners.forEach((listener) => listener());
}

export function subscribeSound(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function preloadSounds(names: SoundName[]): void {
  if (!isSoundEnabled()) return;
  names.forEach((name) => load(name));
}

/** Fire and forget. Never throws and never waits on the network. */
export function playSound(name: SoundName): void {
  if (!isSoundEnabled()) return;
  try {
    const base = load(name);
    if (!base) return;
    const player = base.paused || base.ended ? base : (base.cloneNode(true) as HTMLAudioElement);
    player.volume = SOUNDS[name].volume;
    player.currentTime = 0;
    playing.set(name, player);
    void player.play()?.catch(() => undefined);
  } catch {
    // Missing files, autoplay rules, or no audio device. Visual feedback still shows.
  }
}

export function playSoundOnce(key: string, name: SoundName): boolean {
  if (!once(key)) return false;
  playSound(name);
  return true;
}

/**
 * Runs `callback` after the current `name` sound finishes, or right away if it
 * is not playing. Returns a cancel function.
 */
export function afterSound(name: SoundName, callback: () => void): () => void {
  const player = playing.get(name);
  const active = Boolean(player && !player.paused && !player.ended);
  let done = false;
  let timer = 0;
  const cancel = () => {
    done = true;
    globalThis.clearTimeout(timer);
    player?.removeEventListener("ended", run);
  };
  function run() {
    if (done) return;
    cancel();
    callback();
  }
  if (active && player) {
    const remaining = Number.isFinite(player.duration) ? (player.duration - player.currentTime) * 1000 : MAX_WAIT_MS;
    timer = globalThis.setTimeout(run, Math.min(Math.max(remaining, 0) + 150, MAX_WAIT_MS)) as unknown as number;
    player.addEventListener("ended", run);
  } else {
    timer = globalThis.setTimeout(run, 0) as unknown as number;
  }
  return cancel;
}

/** Plays a spoken clip. Resolves false instead of throwing if playback fails. */
export async function playSpeech(clip: Blob, options: { force?: boolean } = {}): Promise<boolean> {
  if (!options.force && !isSoundEnabled()) return false;
  try {
    speech?.pause();
    const url = URL.createObjectURL(clip);
    const player = new Audio(url);
    const release = () => URL.revokeObjectURL(url);
    player.addEventListener("ended", release, { once: true });
    player.addEventListener("error", release, { once: true });
    speech = player;
    await player.play();
    return true;
  } catch {
    return false;
  }
}

function load(name: SoundName): HTMLAudioElement | null {
  if (typeof Audio === "undefined") return null;
  const cached = loaded.get(name);
  if (cached) return cached;
  const audio = new Audio(SOUNDS[name].src);
  audio.preload = "auto";
  loaded.set(name, audio);
  return audio;
}

function stopAll() {
  playing.forEach((player) => player.pause());
  playing.clear();
  speech?.pause();
  speech = null;
}
