import Link from "next/link";

export function Header() {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-6">
      <Link href="/" className="font-serif text-2xl tracking-tight">
        DineOff
      </Link>
      <nav className="flex items-center gap-2 text-sm">
        <Link href="/join" className="rounded-full px-4 py-2 text-ink-soft hover:text-ink">
          Join
        </Link>
        <Link href="/create" className="rounded-full bg-ink px-4 py-2 text-paper">
          Create dinner
        </Link>
      </nav>
    </header>
  );
}
