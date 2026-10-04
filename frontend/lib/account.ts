import type { AuthUser } from "../types/index.ts";

export const MIN_PASSWORD = 8;
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export type MenuItem = { label: string; href: string } | { label: string; action: "logout" };

export function validateLogin(input: { email: string; password: string }): string | null {
  if (!EMAIL.test(input.email.trim())) return "Enter a valid email address";
  if (!input.password) return "Enter your password";
  return null;
}

/** Mirrors the API rules so most mistakes are caught before a round trip. The API still decides. */
export function validateRegistration(input: {
  displayName: string;
  email: string;
  password: string;
  confirm: string;
}): string | null {
  const name = input.displayName.trim();
  if (!name) return "Tell us what to call you";
  if (name.length > 40) return "Keep your name to 40 characters or fewer";
  if (!EMAIL.test(input.email.trim())) return "Enter a valid email address";
  if (input.password.length < MIN_PASSWORD) return `Use a password with at least ${MIN_PASSWORD} characters`;
  if (input.password.length > 128) return "Use a password with at most 128 characters";
  if (!input.password.trim()) return "Your password can't be only spaces";
  if (input.password !== input.confirm) return "Passwords don't match";
  return null;
}

/** Only same-site paths are allowed after login, so ?next= can't send people elsewhere. */
export function safeNextPath(raw: string | null | undefined, fallback = "/history"): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.includes("\\") || /[\r\n]/.test(raw)) {
    return fallback;
  }
  if (raw.startsWith("/login") || raw.startsWith("/register")) return fallback;
  return raw;
}

export function loginHref(next: string) {
  return `/login?next=${encodeURIComponent(next)}`;
}

/** Items in the account menu. Guests get the way in; members get their pages and log out. */
export function accountMenuItems(user: AuthUser | null): MenuItem[] {
  if (!user) {
    return [
      { label: "Log in", href: "/login" },
      { label: "Create account", href: "/register" },
    ];
  }
  return [
    { label: "History", href: "/history" },
    { label: "Account", href: "/account" },
    { label: "Log out", action: "logout" },
  ];
}

/** Find dinner links. Shown inline on wide screens and inside the menu on phones. */
export const MAIN_LINKS = [
  { label: "Find dinner", href: "/create" },
  { label: "Join", href: "/join" },
] as const;

export function userInitial(user: Pick<AuthUser, "display_name">) {
  return (user.display_name.trim()[0] || "?").toUpperCase();
}

export function memberSince(createdAt: string, timeZone?: string) {
  const date = parseApiDate(createdAt);
  if (!date) return null;
  return date.toLocaleDateString("en-US", { month: "long", year: "numeric", timeZone });
}

/** API datetimes are UTC without an offset. */
export function parseApiDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}
