"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { memberSince, userInitial } from "@/lib/account";
import { NOT_AVAILABLE } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";

export default function AccountPage() {
  const { user, logout } = useRequireUser();
  const router = useRouter();
  const [pending, setPending] = useState(false);

  if (!user) return <p className="pt-16 text-center text-ink-soft">Loading your account...</p>;

  return (
    <section className="mx-auto max-w-md pt-8">
      <div className="form-panel p-8 text-center">
        <span
          aria-hidden="true"
          className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-croc font-serif text-3xl text-moss"
        >
          {userInitial(user)}
        </span>
        <h1 className="mt-4 break-words font-serif text-4xl">{user.display_name}</h1>
        <dl className="mt-8 space-y-5 text-left">
          <div>
            <dt className="text-xs uppercase tracking-[0.18em] text-ink-soft">Email</dt>
            <dd className="mt-1 break-all text-lg">{user.email}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.18em] text-ink-soft">Member since</dt>
            <dd className="mt-1 text-lg">{memberSince(user.created_at) ?? NOT_AVAILABLE}</dd>
          </div>
        </dl>
        <div className="mt-8 flex flex-col gap-3">
          <Link href="/history" className="button-secondary rounded-full px-6 py-3">
            Your dinners
          </Link>
          <button
            type="button"
            disabled={pending}
            onClick={async () => {
              setPending(true);
              await logout();
              router.push("/");
            }}
            className="rounded-full px-6 py-3 text-chili disabled:opacity-60"
          >
            {pending ? "Logging out..." : "Log out"}
          </button>
        </div>
      </div>
    </section>
  );
}
