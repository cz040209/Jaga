/**
 * Swap the refresh-token cookie for a new access token (and rotate the cookie).
 * Called by the browser when it has no access token, or it just expired.
 */

import { NextResponse } from "next/server";

import {
  SERVER_API_URL,
  clearRefreshCookie,
  forwardHeaders,
  readRefreshCookie,
  setRefreshCookie,
} from "@/lib/server/auth-cookie";

export async function POST(request: Request) {
  const refreshToken = await readRefreshCookie();
  if (!refreshToken) {
    return NextResponse.json({ detail: "Not logged in", code: "no_session" }, { status: 401 });
  }

  let response: Response;
  try {
    response = await fetch(`${SERVER_API_URL}/auth/refresh`, {
      method: "POST",
      headers: forwardHeaders(request),
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
  } catch {
    // Backend down: keep the cookie, the session may still be valid later.
    return NextResponse.json(
      { detail: "Can't reach Jaga right now.", code: "backend_unreachable" },
      { status: 502 },
    );
  }

  if (!response.ok) {
    // Expired, revoked, signed out elsewhere, or account frozen: the session is over.
    await clearRefreshCookie();
    return NextResponse.json(
      { detail: "Your session has ended. Please log in again.", code: "session_ended" },
      { status: 401 },
    );
  }

  const tokens = (await response.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  };
  await setRefreshCookie(tokens.refresh_token); // rotated: the old one no longer works
  return NextResponse.json({ access_token: tokens.access_token, expires_in: tokens.expires_in });
}
