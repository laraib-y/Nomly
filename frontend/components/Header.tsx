"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";

import { SoundToggle } from "@/components/SoundToggle";

export function Header() {
  const pathname = usePathname();

  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-6">
      <Link href="/" className="flex items-center gap-2 font-serif text-2xl tracking-tight">
        <Image src="/assets/chef_hat.webp" alt="" width={36} height={36} />
        Nomly
      </Link>
      {pathname !== "/" && !pathname.startsWith("/loading") ? (
        <nav className="flex items-center gap-2 text-sm">
          <SoundToggle />
          <Link href="/join" className="rounded-full px-4 py-2 text-ink-soft hover:text-ink">
            Join
          </Link>
          <Link href="/create" className="button-primary rounded-full px-4 py-2">
            Create dinner
          </Link>
        </nav>
      ) : null}
    </header>
  );
}
