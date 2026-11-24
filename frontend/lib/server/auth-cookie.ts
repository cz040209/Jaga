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
export const SERVER_API_URL =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

export async function setRefreshCookie(token: string): Promise<void> {
  (await cookies()).set(REFRESH_COOKIE, token, {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
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

/** Forward the browser's user agent, so the backend can label the device. */
export function forwardHeaders(request: Request): HeadersInit {
  return {
    "Content-Type": "application/json",
    "User-Agent": request.headers.get("user-agent") ?? "jaga-web",
  };
}
