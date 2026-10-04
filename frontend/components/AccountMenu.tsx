"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";

import { useAuth } from "@/components/AuthProvider";
import { type MenuItem, MAIN_LINKS, accountMenuItems, userInitial } from "@/lib/account";

/** Small dropdown. Closes on outside click, Escape, and navigation. */
function Dropdown({
  label,
  trigger,
  items,
  className = "",
}: {
  label: string;
  trigger: ReactNode;
  items: MenuItem[];
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuth();

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const itemClass = "block w-full rounded-xl px-4 py-2.5 text-left hover:bg-paper";

  return (
    <div ref={root} className={`relative ${className}`}>
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-2 rounded-full border border-line bg-card px-2 py-1.5 text-ink"
      >
        {trigger}
      </button>
      {open ? (
        <div
          id={menuId}
          role="menu"
          className="absolute right-0 z-40 mt-2 w-52 rounded-2xl border border-line bg-card p-1.5 shadow-card"
        >
          {items.map((item) =>
            "href" in item ? (
              <Link key={item.label} href={item.href} role="menuitem" className={`${itemClass} text-ink`}>
                {item.label}
              </Link>
            ) : (
              <button
                key={item.label}
                type="button"
                role="menuitem"
                className={`${itemClass} text-chili`}
                onClick={async () => {
                  setOpen(false);
                  await logout();
                  router.push("/");
                }}
              >
                {item.label}
              </button>
            ),
          )}
        </div>
      ) : null}
    </div>
  );
}

function Avatar({ initial }: { initial: string }) {
  return (
    <span
      aria-hidden="true"
      className="flex h-7 w-7 items-center justify-center rounded-full bg-croc font-serif text-sm text-moss"
    >
      {initial}
    </span>
  );
}

/** Account entry for wide screens: "Log in" for guests, the user's name and a menu for members. */
export function AccountMenu() {
  const { user, loading } = useAuth();
  if (loading) return <span className="hidden h-10 w-24 sm:block" aria-hidden="true" />;
  if (!user) {
    return (
      <Link href="/login" className="hidden rounded-full px-4 py-2 text-ink-soft hover:text-ink sm:inline-block">
        Log in
      </Link>
    );
  }
  return (
    <Dropdown
      className="hidden sm:block"
      label={`Account menu for ${user.display_name}`}
      items={accountMenuItems(user)}
      trigger={
        <>
          <Avatar initial={userInitial(user)} />
          <span className="max-w-[10rem] truncate pr-2">{user.display_name}</span>
        </>
      }
    />
  );
}

/** Phones get one compact menu holding dinner links and the account entries. */
export function MobileMenu({ showDinnerLinks }: { showDinnerLinks: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  const items: MenuItem[] = [...(showDinnerLinks ? MAIN_LINKS.map((link) => ({ ...link })) : []), ...accountMenuItems(user)];
  return (
    <Dropdown
      className="sm:hidden"
      label={user ? `Menu for ${user.display_name}` : "Menu"}
      items={items}
      trigger={
        user ? (
          <Avatar initial={userInitial(user)} />
        ) : (
          <span aria-hidden="true" className="flex h-7 w-7 items-center justify-center text-lg leading-none">
            ☰
          </span>
        )
      }
    />
  );
}
