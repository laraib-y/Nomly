"use client";

import { useEffect, useRef, useState } from "react";

import { speakConcierge, transcribeAudio } from "@/lib/api";
import { isSoundEnabled, playSpeech } from "@/lib/audio";

export type VoiceState = "idle" | "requesting-permission" | "recording" | "transcribing" | "complete" | "error";

function preferredMimeType() {
  if (typeof MediaRecorder === "undefined") return "";
  if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) return "audio/webm;codecs=opus";
  if (MediaRecorder.isTypeSupported("audio/webm")) return "audio/webm";
  return "";
}

export function useVoice(onTranscript: (transcript: string) => void) {
  const [state, setState] = useState<VoiceState>("idle");
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const sessionRef = useRef(0);
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  useEffect(() => {
    return () => {
      sessionRef.current += 1;
      recorderRef.current?.stop();
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  function releaseStream() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
  }

  async function start() {
    if (state === "recording" || state === "transcribing" || state === "requesting-permission") return;
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setState("error");
      setError("This browser cannot record audio. You can type your dinner plans instead.");
      return;
    }

    const session = sessionRef.current + 1;
    sessionRef.current = session;
    setState("requesting-permission");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (sessionRef.current !== session) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      const mimeType = preferredMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        releaseStream();
        void finish(blob, session);
      };
      streamRef.current = stream;
      recorderRef.current = recorder;
      recorder.start();
      setState("recording");
    } catch (err) {
      releaseStream();
      setState("error");
      const name = err instanceof DOMException ? err.name : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        setError("Microphone access was denied. You can type your dinner plans instead.");
      } else if (name === "NotFoundError") {
        setError("No microphone was found. You can type your dinner plans instead.");
      } else {
        setError("Voice is temporarily unavailable. You can type your dinner plans instead.");
      }
    }
  }

  function stop() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      sessionRef.current += 1;
      if (state === "requesting-permission") setState("idle");
      return;
    }
    recorder.stop();
  }

  async function finish(blob: Blob, session: number) {
    if (sessionRef.current !== session) return;
    if (blob.size < 100) {
      setState("error");
      setError("That recording was empty. Try again or type your dinner plans instead.");
      return;
    }
    setState("transcribing");
    try {
      const transcript = await transcribeAudio(blob);
      if (sessionRef.current !== session) return;
      onTranscriptRef.current(transcript);
      setState("complete");
      setError(null);
      void playConfirmation(transcript);
    } catch (err) {
      if (sessionRef.current !== session) return;
      setState("error");
      setError(err instanceof Error ? err.message : "We couldn't understand that recording. Try again or type your dinner plans instead.");
    }
  }

  function reset() {
    sessionRef.current += 1;
    recorderRef.current?.stop();
    releaseStream();
    setError(null);
    setState("idle");
  }

  return { state, error, start, stop, reset };
}

async function playConfirmation(transcript: string) {
  if (!isSoundEnabled()) return;
  const audio = await speakConcierge(`Got it. ${transcript}`.slice(0, 400));
  if (audio) await playSpeech(audio);
}
