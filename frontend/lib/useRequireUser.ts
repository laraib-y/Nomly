"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/AuthProvider";
import { loginHref } from "@/lib/account";

/** Sends guests to log in and back here afterwards. The API enforces access either way. */
export function useRequireUser() {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!auth.loading && !auth.user) router.replace(loginHref(pathname));
  }, [auth.loading, auth.user, pathname, router]);

  return auth;
}
