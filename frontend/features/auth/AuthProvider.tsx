"use client";

/**
 * Knows whether the user is logged in, and offers login / register / logout.
 *
 * On first load it asks /api/auth/refresh for an access token (works when
 * the session cookie is still valid). If any API call later finds the session
 * has ended, the token store is cleared and `status` becomes "anonymous".
 */

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { refreshAccessToken } from "@/lib/api/client";
import { toApiError } from "@/lib/api/errors";
import { tokenStore } from "@/lib/auth/token-store";
import { getDeviceFingerprint } from "@/lib/fingerprint";
import type { Customer, Language } from "@/types";

type Status = "loading" | "authenticated" | "anonymous";

export type LoginInput = { email: string; password: string };
export type RegisterInput = {
  full_name: string;
  email: string;
  phone_number: string;
  password: string;
  preferred_language: Language;
};

type SessionResult = { customer: Customer; is_new_device: boolean };

type AuthContextValue = {
  status: Status;
  login: (input: LoginInput) => Promise<SessionResult>;
  register: (input: RegisterInput) => Promise<SessionResult>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

async function startSession(
  path: "/api/auth/login" | "/api/auth/register",
  input: LoginInput | RegisterInput,
): Promise<SessionResult & { access_token: string }> {
  const device_fingerprint = await getDeviceFingerprint();
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, ...(device_fingerprint ? { device_fingerprint } : {}) }),
  });
  if (!response.ok) throw await toApiError(response);
  return response.json();
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>(() =>
    tokenStore.get() ? "authenticated" : "loading",
  );

  // React to the token appearing or disappearing anywhere in the app.
  useEffect(
    () => tokenStore.subscribe((token) => setStatus(token ? "authenticated" : "anonymous")),
    [],
  );

  // First load: try to resume the session from the cookie.
  useEffect(() => {
    if (!tokenStore.get()) void refreshAccessToken();
  }, []);

  const begin = useCallback(
    async (path: "/api/auth/login" | "/api/auth/register", input: LoginInput | RegisterInput) => {
      const result = await startSession(path, input);
      queryClient.clear(); // never show the previous user's cached data
      tokenStore.set(result.access_token);
      return { customer: result.customer, is_new_device: result.is_new_device };
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    tokenStore.set(null);
    queryClient.clear();
    router.replace("/welcome");
  }, [queryClient, router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      login: (input) => begin("/api/auth/login", input),
      register: (input) => begin("/api/auth/register", input),
      logout,
    }),
    [status, begin, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
