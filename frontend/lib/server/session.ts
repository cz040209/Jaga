/**
 * SERVER ONLY. Shared by /api/auth/login and /api/auth/register.
 *
 * Calls FastAPI, keeps the refresh token in the httpOnly cookie, and gives the
 * browser only what it needs: the customer, a short-lived access token and
 * whether this was a new device. The refresh token never reaches JavaScript.
 */

import "server-only";
import { NextResponse } from "next/server";

import { SERVER_API_URL, forwardHeaders, setRefreshCookie } from "@/lib/server/auth-cookie";

type BackendAuthResponse = {
  customer: unknown;
  tokens: { access_token: string; refresh_token: string; expires_in: number };
  is_new_device: boolean;
};

export async function startSession(
  request: Request,
  backendPath: "/auth/login" | "/auth/register",
): Promise<NextResponse> {
  let body: string;
  try {
    body = JSON.stringify(await request.json());
  } catch {
    return NextResponse.json({ detail: "Invalid request", code: "bad_request" }, { status: 400 });
  }

  let response: Response;
  try {
    response = await fetch(`${SERVER_API_URL}${backendPath}`, {
      method: "POST",
      headers: forwardHeaders(request),
      body,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Can't reach Jaga right now. Please try again.", code: "backend_unreachable" },
      { status: 502 },
    );
  }

  const data: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    // Pass errors through unchanged ({detail, code} or 422 field errors).
    return NextResponse.json(data, { status: response.status });
  }

  const auth = data as BackendAuthResponse;
  await setRefreshCookie(auth.tokens.refresh_token);
  return NextResponse.json(
    {
      customer: auth.customer,
      access_token: auth.tokens.access_token,
      expires_in: auth.tokens.expires_in,
      is_new_device: auth.is_new_device,
    },
    { status: response.status },
  );
}
