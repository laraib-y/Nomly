import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { afterEach, beforeEach, test } from "node:test";

const account = await import("../lib/account.ts");
const api = await import("../lib/api.ts");
const { accountMenuItems, memberSince, safeNextPath, userInitial, validateLogin, validateRegistration, MAIN_LINKS } = account;

const USER = { id: "u1", email: "abdalla@example.com", display_name: "Abdalla", created_at: "2026-09-12T18:00:00" };

type Call = { url: string; init: RequestInit };
let calls: Call[] = [];
const realFetch = globalThis.fetch;
const stored: string[] = [];

function respond(status: number, body?: unknown) {
  globalThis.fetch = (async (url: string, init: RequestInit = {}) => {
    calls.push({ url, init });
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
    });
  }) as typeof fetch;
}

beforeEach(() => {
  calls = [];
  stored.length = 0;
  const trap = { setItem: (key: string) => stored.push(key), getItem: () => null, removeItem() {}, clear() {}, key: () => null, length: 0 };
  Object.assign(globalThis, { localStorage: trap, sessionStorage: trap });
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

// Login and registration forms

test("login needs an email and a password", () => {
  assert.equal(validateLogin({ email: "nope", password: "x" }), "Enter a valid email address");
  assert.equal(validateLogin({ email: "a@b.co", password: "" }), "Enter your password");
  assert.equal(validateLogin({ email: " a@b.co ", password: "anything" }), null);
});

test("registration asks only for name, email, password and confirmation", () => {
  const ok = { displayName: "Abdalla", email: "a@b.co", password: "long enough", confirm: "long enough" };
  assert.equal(validateRegistration(ok), null);
  assert.equal(validateRegistration({ ...ok, displayName: "  " }), "Tell us what to call you");
  assert.equal(validateRegistration({ ...ok, email: "a@b" }), "Enter a valid email address");
  assert.equal(validateRegistration({ ...ok, password: "short", confirm: "short" }), "Use a password with at least 8 characters");
  assert.equal(validateRegistration({ ...ok, password: "        ", confirm: "        " }), "Your password can't be only spaces");
  assert.equal(validateRegistration({ ...ok, confirm: "different" }), "Passwords don't match");
  const form = readFileSync("components/AuthForm.tsx", "utf8");
  for (const field of ["Your name", "Email", "Password", "Confirm password"]) assert.match(form, new RegExp(`>${field}<`));
  assert.doesNotMatch(form, /phone|birthday|address|avatar/i);
});

test("after login only same-site paths are followed", () => {
  assert.equal(safeNextPath("/history/abc"), "/history/abc");
  assert.equal(safeNextPath(null), "/history");
  assert.equal(safeNextPath("https://evil.example"), "/history");
  assert.equal(safeNextPath("//evil.example"), "/history");
  assert.equal(safeNextPath("/\\evil.example"), "/history");
  assert.equal(safeNextPath("/login"), "/history");
  assert.equal(safeNextPath(undefined, "/create"), "/create");
});

// Authentication state through the API client

test("login sends credentials with the request and returns the user", async () => {
  respond(200, USER);
  const user = await api.login({ email: "abdalla@example.com", password: "secret pass" });
  assert.deepEqual(user, USER);
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /\/api\/auth\/login$/);
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.credentials, "include");
  assert.deepEqual(JSON.parse(String(calls[0].init.body)), { email: "abdalla@example.com", password: "secret pass" });
  assert.deepEqual(stored, [], "nothing about the session is written to browser storage");
});

test("registration posts the four allowed fields and surfaces API errors", async () => {
  respond(201, USER);
  await api.register({ email: "a@b.co", password: "long enough", display_name: "Abdalla" });
  assert.deepEqual(Object.keys(JSON.parse(String(calls[0].init.body))).sort(), ["display_name", "email", "password"]);
  respond(409, { detail: "An account with that email already exists" });
  await assert.rejects(api.register({ email: "a@b.co", password: "long enough", display_name: "A" }), /already exists/);
});

test("/me restores the session, and a 401 means guest rather than an error", async () => {
  respond(200, USER);
  assert.deepEqual(await api.getMe(), USER);
  assert.equal(calls[0].init.credentials, "include");
  respond(401, { detail: "Log in to continue" });
  assert.equal(await api.getMe(), null);
  respond(500, { detail: "boom" });
  await assert.rejects(api.getMe(), /boom/);
});

test("logout handles the empty 204 reply", async () => {
  respond(204);
  assert.equal(await api.logout(), undefined);
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.credentials, "include");
});

test("dinner creation carries the cookie so signed-in dinners are saved", async () => {
  respond(201, { room_code: "ABC123" });
  await api.createSession({ description: "Ramen", nickname: "A", location: "Burnaby", group_size: 3 });
  assert.equal(calls[0].init.credentials, "include");
});

test("auth code never touches browser storage, cookies, or URLs for tokens", () => {
  for (const file of ["components/AuthProvider.tsx", "components/AuthForm.tsx", "components/AccountMenu.tsx", "lib/account.ts", "lib/api.ts", "lib/useRequireUser.ts"]) {
    const text = readFileSync(file, "utf8");
    assert.doesNotMatch(text, /localStorage|sessionStorage|document\.cookie/, file);
    assert.doesNotMatch(text, /[?&]token=|access_token|Authorization/, file);
  }
  assert.doesNotMatch(readFileSync("lib/storage.ts", "utf8"), /token|password/i);
});

// Navigation and account page

test("account menu gives guests a way in and members History, Account, Log out", () => {
  assert.deepEqual(accountMenuItems(null), [
    { label: "Log in", href: "/login" },
    { label: "Create account", href: "/register" },
  ]);
  assert.deepEqual(accountMenuItems(USER), [
    { label: "History", href: "/history" },
    { label: "Account", href: "/account" },
    { label: "Log out", action: "logout" },
  ]);
});

test("mobile navigation collapses dinner and account links into one compact menu", () => {
  assert.deepEqual(MAIN_LINKS.map((link) => link.href), ["/create", "/join"]);
  const header = readFileSync("components/Header.tsx", "utf8");
  const menu = readFileSync("components/AccountMenu.tsx", "utf8");
  assert.match(header, /<MobileMenu/);
  assert.match(menu, /className="sm:hidden"/);
  assert.match(menu, /aria-haspopup="menu"/);
  assert.match(menu, /aria-expanded=\{open\}/);
  assert.match(menu, /Escape/);
  for (const link of header.match(/href="\/(join|create)"[^>]*/g) ?? []) assert.match(link, /hidden .*sm:inline-block/);
});

test("account page details", () => {
  assert.equal(userInitial({ display_name: " abdalla" }), "A");
  assert.equal(memberSince(USER.created_at, "UTC"), "September 2026");
  assert.equal(memberSince("garbage"), null);
  const page = readFileSync("app/account/page.tsx", "utf8");
  for (const text of ["Email", "Member since", "Log out"]) assert.match(page, new RegExp(text));
});
