"use client";

import { useVoice } from "@/lib/useVoice";

export function VoiceInput({ onTranscript }: { onTranscript: (transcript: string) => void }) {
  const voice = useVoice(onTranscript);
  const recording = voice.state === "recording";
  const busy = voice.state === "requesting-permission" || voice.state === "transcribing";

  return (
    <div className="rounded-3xl border border-line bg-paper px-4 py-4">
      <div className="flex items-center gap-4">
        <button
          type="button"
          disabled={busy}
          onPointerDown={(event) => {
            event.preventDefault();
            event.currentTarget.setPointerCapture(event.pointerId);
            void voice.start();
          }}
          onPointerUp={() => voice.stop()}
          onPointerCancel={() => voice.stop()}
          className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-lg text-white disabled:opacity-60 ${
            recording ? "bg-chili" : "bg-ink"
          }`}
          aria-label={recording ? "Release to finish" : "Hold to talk"}
        >
          {recording ? "●" : "🎙"}
        </button>
        <div className="min-w-0 flex-1">
          {voice.state === "idle" || voice.state === "complete" ? (
            <p className="font-medium">Hold to talk</p>
          ) : null}
          {voice.state === "requesting-permission" ? <p className="font-medium">Allow the microphone to continue.</p> : null}
          {recording ? (
            <div>
              <p className="font-medium text-chili">Listening...</p>
              <div className="voice-bars mt-2 flex h-6 items-end gap-1" aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
                <span />
              </div>
              <p className="mt-1 text-sm text-ink-soft">Release when you&apos;re done.</p>
            </div>
          ) : null}
          {voice.state === "transcribing" ? <p className="font-medium">Understanding your request...</p> : null}
          {voice.state === "error" ? <p className="text-sm text-chili">{voice.error}</p> : null}
          {voice.state === "complete" ? (
            <p className="text-sm text-ink-soft">You can edit what you said, then find dinner.</p>
          ) : null}
          {voice.state === "idle" ? (
            <p className="text-sm text-ink-soft">Speak your dinner plans, or keep typing below.</p>
          ) : null}
        </div>
        {voice.state === "complete" || voice.state === "error" ? (
          <button type="button" onClick={voice.reset} className="text-sm text-ink-soft underline">
            Try again
          </button>
        ) : null}
      </div>
    </div>
  );
}
