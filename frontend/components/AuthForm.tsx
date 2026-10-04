"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { login, register } from "@/lib/api";
import { MIN_PASSWORD, safeNextPath, validateLogin, validateRegistration } from "@/lib/account";

type Mode = "login" | "register";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const params = useSearchParams();
  const { user, loading, setUser } = useAuth();
  const next = safeNextPath(params.get("next"), mode === "login" ? "/history" : "/create");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  // Already signed in when the page opened. After a submit, onSubmit does the one navigation.
  useEffect(() => {
    if (!loading && user && !pending) router.replace(next);
  }, [loading, next, pending, router, user]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const problem =
      mode === "login" ? validateLogin({ email, password }) : validateRegistration({ displayName, email, password, confirm });
    if (problem) {
      setError(problem);
      return;
    }
    setPending(true);
    setError(null);
    try {
      const account =
        mode === "login"
          ? await login({ email: email.trim(), password })
          : await register({ email: email.trim(), password, display_name: displayName.trim() });
      setUser(account);
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
      setPending(false);
    }
  }

  const otherHref = `${mode === "login" ? "/register" : "/login"}${params.get("next") ? `?next=${encodeURIComponent(next)}` : ""}`;

  return (
    <section className="mx-auto w-full max-w-[440px] px-2 pt-6 text-center sm:pt-10">
      <p className="font-serif text-4xl tracking-tight">Nomly</p>
      <h1 className="mt-3 font-serif text-2xl leading-snug text-ink-soft">
        Stop arguing.
        <br />
        Let the group decide.
      </h1>
      <form onSubmit={onSubmit} noValidate className="form-panel mt-8 space-y-4 p-6 text-left sm:p-8">
        {mode === "register" ? (
          <label className="block">
            <span>Your name</span>
            <input
              required
              autoComplete="nickname"
              maxLength={40}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Abdalla"
              className="form-field mt-1.5"
            />
          </label>
        ) : null}
        <label className="block">
          <span>Email</span>
          <input
            required
            type="email"
            autoComplete="email"
            inputMode="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="form-field mt-1.5"
          />
        </label>
        <label className="block">
          <span>Password</span>
          <input
            required
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={mode === "register" ? MIN_PASSWORD : undefined}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="form-field mt-1.5"
          />
          {mode === "register" ? (
            <span className="mt-1 block text-sm text-ink-soft">At least {MIN_PASSWORD} characters.</span>
          ) : null}
        </label>
        {mode === "register" ? (
          <label className="block">
            <span>Confirm password</span>
            <input
              required
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              className="form-field mt-1.5"
            />
          </label>
        ) : null}
        {error ? (
          <p role="alert" className="form-error text-sm">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={pending}
          className="button-primary w-full rounded-2xl py-3 text-lg disabled:opacity-60"
        >
          {pending ? (mode === "login" ? "Logging in..." : "Creating account...") : mode === "login" ? "Log in" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-ink-soft">
        {mode === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
        <Link href={otherHref} className="text-ink underline underline-offset-4">
          {mode === "login" ? "Create one" : "Log in"}
        </Link>
      </p>
      <p className="mt-2 text-sm text-ink-soft">
        No account needed to join a dinner.{" "}
        <Link href="/join" className="underline underline-offset-4">
          Join with a code
        </Link>
      </p>
    </section>
  );
}
