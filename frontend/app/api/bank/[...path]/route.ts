/**
 * The browser's only door to the backend: /api/bank/<path> → FastAPI /<path>.
 *
 * The page and its data now come from ONE address (this Next.js server), so:
 *   - a phone on Wi-Fi, a Cloudflare tunnel or Docker all just work
 *     (the browser never needs to know where FastAPI lives);
 *   - there's no cross-origin call, so no CORS.
 *
 * Only the headers the API needs are passed on (an allow-list, not a copy of
 * everything), plus the caller's IP so the backend still knows who's calling.
 */

import { NextResponse, type NextRequest } from "next/server";

import { SERVER_API_URL, clientIp } from "@/lib/server/auth-cookie";

export const dynamic = "force-dynamic"; // never cache bank data

const REQUEST_HEADERS = ["authorization", "content-type", "accept", "idempotency-key", "user-agent"];
const RESPONSE_HEADERS = ["content-type", "idempotent-replayed", "www-authenticate"];

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, { params }: Context): Promise<Response> {
  const { path } = await params;
  const target = new URL(`${SERVER_API_URL}/${path.map(encodeURIComponent).join("/")}`);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const ip = clientIp(request);
  if (ip) headers.set("x-forwarded-for", ip);

  let response: Response;
  try {
    response = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" ? undefined : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return NextResponse.json(
      { detail: "Can't reach Jaga right now. Please try again.", code: "backend_unreachable" },
      { status: 502 },
    );
  }

  const outHeaders = new Headers({ "cache-control": "no-store" });
  for (const name of RESPONSE_HEADERS) {
    const value = response.headers.get(name);
    if (value) outHeaders.set(name, value);
  }
  const body = response.status === 204 ? null : response.body;
  return new Response(body, { status: response.status, headers: outHeaders });
}

export { forward as GET, forward as POST, forward as PATCH, forward as DELETE };
