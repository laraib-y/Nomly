"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";

export function Header() {
  const pathname = usePathname();

  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-6">
      <Link href="/" className="flex items-center gap-2 font-serif text-2xl tracking-tight">
        <Image src="/assets/chef_hat.webp" alt="" width={36} height={36} />
        Nomly
      </Link>
      {pathname !== "/" ? (
        <nav className="flex items-center gap-2 text-sm">
          <Link href="/join" className="rounded-full px-4 py-2 text-ink-soft hover:text-ink">
            Join
          </Link>
          <Link href="/create" className="rounded-full bg-ink px-4 py-2 text-paper">
            Create dinner
          </Link>
        </nav>
      ) : null}
    </header>
  );
}
