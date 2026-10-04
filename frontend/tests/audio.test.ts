// Run with: npm test   (Node's built-in test runner, no extra dependencies)
import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

const plays: string[] = [];
let rejectPlay = false;
let throwOnCreate = false;

class FakeAudio extends EventTarget {
  src: string;
  paused = true;
  ended = false;
  volume = 1;
  currentTime = 0;
  duration = Number.NaN;
  preload = "";

  constructor(src = "") {
    super();
    if (throwOnCreate) throw new Error("no audio device");
    this.src = src;
  }

  play() {
    plays.push(this.src);
    return rejectPlay ? Promise.reject(new Error("NotAllowedError")) : Promise.resolve();
  }

  pause() {
    this.paused = true;
  }

  cloneNode() {
    return new FakeAudio(this.src);
  }
}

const store = new Map<string, string>();
Object.assign(globalThis, {
  Audio: FakeAudio,
  localStorage: {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => void store.set(key, value),
  },
});
URL.createObjectURL = () => "blob:nomly";
URL.revokeObjectURL = () => undefined;

const audio = await import("../lib/audio.ts");

beforeEach(() => {
  plays.length = 0;
  rejectPlay = false;
  throwOnCreate = false;
  store.clear();
});

test("each swipe decision plays its own sound", () => {
  const expected = {
    like: "/audio/swipes/like.mp3",
    pass: "/audio/swipes/pass.mp3",
    super_like: "/audio/swipes/superlike.mp3",
    veto: "/audio/swipes/veto.mp3",
  } as const;
  for (const [decision, src] of Object.entries(expected)) {
    plays.length = 0;
    audio.playSound(audio.soundForDecision(decision as keyof typeof expected));
    assert.deepEqual(plays, [src]);
  }
});

test("blocked playback never throws or waits, so the swipe still goes out", async () => {
  rejectPlay = true;
  const returned = audio.playSound("like") as unknown;
  assert.equal(returned, undefined);
  await new Promise((resolve) => setTimeout(resolve, 0));
});

test("sound off silences effects and is remembered", () => {
  audio.setSoundEnabled(false);
  assert.equal(audio.isSoundEnabled(), false);
  assert.equal(store.get("nomly:sound"), "off");
  audio.playSound("like");
  assert.deepEqual(plays, []);
  audio.setSoundEnabled(true);
  audio.playSound("like");
  assert.equal(plays.length, 1);
});

test("sound defaults to on", () => {
  assert.equal(audio.isSoundEnabled(), true);
});

test("room events map to join, finished, and matching sounds", () => {
  const join = audio.soundForRoomEvent("abc123", { type: "participant_joined", participant: { id: "p2" } }, null);
  assert.deepEqual(join, { sound: "join", key: "join:ABC123:p2" });

  const finished = audio.soundForRoomEvent("ABC123", { type: "swipe_progress", finished: 1, total: 3 }, 0);
  assert.deepEqual(finished, { sound: "participant-finished", key: "finished:ABC123:1" });

  const matching = audio.soundForRoomEvent("ABC123", { type: "all_completed", finished: 3, total: 3 }, 2);
  assert.deepEqual(matching, { sound: "matching", key: "matching:ABC123" });
});

test("ordinary swipes and the first state snapshot do not play the finished sound", () => {
  assert.equal(audio.soundForRoomEvent("R", { type: "swipe_progress", finished: 1, total: 3 }, 1), null);
  assert.equal(audio.soundForRoomEvent("R", { type: "swipe_progress", finished: 1, total: 3 }, null), null);
  assert.equal(audio.soundForRoomEvent("R", { type: "state", finished: 2, total: 3 }, null), null);
  assert.equal(audio.soundForRoomEvent("R", { type: "dinner_started" }, 0), null);
});

test("matching plays once even when the API reply and the WebSocket both report it", () => {
  assert.equal(audio.playSoundOnce("matching:ONCE1", "matching"), true);
  assert.equal(audio.playSoundOnce("matching:ONCE1", "matching"), false);
  assert.deepEqual(plays, ["/audio/matching/matching.mp3"]);
});

test("winner plays once across rerenders", () => {
  for (let render = 0; render < 4; render += 1) audio.playSoundOnce("winner:ONCE2", "winner");
  assert.deepEqual(plays, ["/audio/matching/winner.mp3"]);
});

test("afterSound runs right away when nothing is playing", async () => {
  let ran = false;
  audio.afterSound("matching", () => {
    ran = true;
  });
  await new Promise((resolve) => setTimeout(resolve, 5));
  assert.equal(ran, true);
});

test("afterSound can be cancelled", async () => {
  let ran = false;
  const cancel = audio.afterSound("winner", () => {
    ran = true;
  });
  cancel();
  await new Promise((resolve) => setTimeout(resolve, 5));
  assert.equal(ran, false);
});

test("speech failure resolves false instead of throwing", async () => {
  rejectPlay = true;
  assert.equal(await audio.playSpeech(new Blob(["x"])), false);
});

test("speech respects sound off unless the user asked for it", async () => {
  audio.setSoundEnabled(false);
  assert.equal(await audio.playSpeech(new Blob(["x"])), false);
  assert.equal(plays.length, 0);
  assert.equal(await audio.playSpeech(new Blob(["x"]), { force: true }), true);
  audio.setSoundEnabled(true);
});

test("no audio support fails silently", async () => {
  throwOnCreate = true;
  assert.equal(await audio.playSpeech(new Blob(["x"]), { force: true }), false);
});
