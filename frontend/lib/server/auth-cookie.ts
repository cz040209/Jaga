/**
 * SERVER ONLY. The refresh token lives in an httpOnly cookie that browser
 * JavaScript can never read, so an injected script can't steal a 30-day login.
 * Only our /api/auth/* route handlers touch it.
 */

import "server-only";
import { cookies } from "next/headers";

export const REFRESH_COOKIE = "jaga_rt";
const THIRTY_DAYS = 60 * 60 * 24 * 30;

/** Where the Next.js server reaches FastAPI (server-to-server). */
export const SERVER_API_URL = process.env.API_URL ?? "http://localhost:8010";

export async function setRefreshCookie(token: string): Promise<void> {
  (await cookies()).set(REFRESH_COOKIE, token, {
    httpOnly: true,
    sameSite: "strict",
    // Secure = only sent over https. On by default in production, but the
    // Docker setup runs plain http://localhost (and phones on Wi-Fi), so it
    // can be switched off with COOKIE_SECURE=false.
    secure: process.env.COOKIE_SECURE
      ? process.env.COOKIE_SECURE === "true"
      : process.env.NODE_ENV === "production",
    path: "/",
    maxAge: THIRTY_DAYS,
  });
}

export async function readRefreshCookie(): Promise<string | undefined> {
  return (await cookies()).get(REFRESH_COOKIE)?.value;
}

export async function clearRefreshCookie(): Promise<void> {
  (await cookies()).delete(REFRESH_COOKIE);
}

/**
 * The caller's IP as Next.js saw it. Every request reaches FastAPI through
 * this server, so without passing it on the backend would only ever see
 * Next.js's own address (useless for "new location" fraud checks).
 * Uvicorn trusts X-Forwarded-For from 127.0.0.1 by default.
 */
export function clientIp(request: Request): string | null {
  return request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || null;
}

/** Forward the browser's user agent and IP, so the backend can label the device and location. */
export function forwardHeaders(request: Request): HeadersInit {
  const ip = clientIp(request);
  return {
    "Content-Type": "application/json",
    "User-Agent": request.headers.get("user-agent") ?? "jaga-web",
    ...(ip ? { "X-Forwarded-For": ip } : {}),
  };
}
