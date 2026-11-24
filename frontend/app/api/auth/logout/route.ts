/** End this device's session on the backend, then drop the cookie. Always succeeds. */

import { NextResponse } from "next/server";

import {
  SERVER_API_URL,
  clearRefreshCookie,
  forwardHeaders,
  readRefreshCookie,
} from "@/lib/server/auth-cookie";

export async function POST(request: Request) {
  const refreshToken = await readRefreshCookie();
  if (refreshToken) {
    await fetch(`${SERVER_API_URL}/auth/logout`, {
      method: "POST",
      headers: forwardHeaders(request),
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    }).catch(() => undefined); // backend down: still log out locally
  }
  await clearRefreshCookie();
  return new NextResponse(null, { status: 204 });
}
