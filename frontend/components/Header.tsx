"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";

import { AccountMenu, MobileMenu } from "@/components/AccountMenu";
import { useAuth } from "@/components/AuthProvider";
import { SoundToggle } from "@/components/SoundToggle";

export function Header() {
  const pathname = usePathname();
  const { user } = useAuth();
  const loadingScreen = pathname.startsWith("/loading");
  const dinnerLinks = pathname !== "/" && !loadingScreen;

  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-6">
      <Link href="/" className="flex items-center gap-2 font-serif text-2xl tracking-tight">
        <Image src="/assets/chef_hat.webp" alt="" width={36} height={36} />
        Nomly
      </Link>
      {loadingScreen ? null : (
        <nav className="flex items-center gap-2 text-sm" aria-label="Main">
          {dinnerLinks ? <SoundToggle /> : null}
          {dinnerLinks ? (
            <>
              <Link href="/join" className="hidden rounded-full px-4 py-2 text-ink-soft hover:text-ink sm:inline-block">
                Join
              </Link>
              <Link href="/create" className="button-primary hidden rounded-full px-4 py-2 sm:inline-block">
                Create dinner
              </Link>
            </>
          ) : null}
          {user ? (
            <Link
              href="/history"
              aria-current={pathname.startsWith("/history") ? "page" : undefined}
              className="hidden rounded-full px-4 py-2 text-ink-soft hover:text-ink aria-[current=page]:text-ink sm:inline-block"
            >
              History
            </Link>
          ) : null}
          <AccountMenu />
          <MobileMenu showDinnerLinks={dinnerLinks} />
        </nav>
      )}
    </header>
  );
}
