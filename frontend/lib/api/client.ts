/**
 * Every call from the browser to the FastAPI backend goes through `api()`.
 *
 * It adds the access token, and when the token is missing or expired
 * (401) it gets a fresh one from /api/auth/refresh and retries ONCE.
 * If that also fails, the session is over: the token store is cleared and
 * the AuthProvider sends the user to the login screen.
 */

import { tokenStore } from "@/lib/auth/token-store";
import { ApiError, networkError, toApiError } from "@/lib/api/errors";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

let refreshing: Promise<string | null> | null = null;

/**
 * Ask our own Next.js server for a new access token (it holds the refresh
 * token in an httpOnly cookie). Concurrent callers share one request, so
 * five queries failing at once don't trigger five refreshes.
 */
export function refreshAccessToken(): Promise<string | null> {
  refreshing ??= fetch("/api/auth/refresh", { method: "POST" })
    .then(async (response) => {
      if (!response.ok) return null;
      const data = (await response.json()) as { access_token: string };
      return data.access_token;
    })
    .catch(() => null)
    .then((token) => {
      tokenStore.set(token);
      return token;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
};

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const send = (token: string | null) =>
    fetch(`${API_URL}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

  let response: Response;
  try {
    const stored = tokenStore.get();
    let token = stored ?? (await refreshAccessToken());
    response = await send(token);
    if (response.status === 401 && stored) {
      token = await refreshAccessToken(); // expired: one refresh, one retry
      if (token) response = await send(token);
    }
  } catch {
    throw networkError();
  }

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export { ApiError };
