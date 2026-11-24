/**
 * Runs before a page loads. A quick first check only: "is there a session
 * cookie at all?" The real check (is the session still valid?) happens when
 * the page asks /api/auth/refresh for an access token.
 */

import { NextResponse, type NextRequest } from "next/server";

const REFRESH_COOKIE = "jaga_rt";
const BANK_PAGES = ["/home", "/history", "/payees", "/transfer", "/transfers", "/inbox", "/profile"];
const GUEST_PAGES = ["/welcome", "/login", "/register"];

function startsWithAny(path: string, prefixes: string[]): boolean {
  return prefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(REFRESH_COOKIE);

  if (pathname === "/") {
    return NextResponse.redirect(new URL(hasSession ? "/home" : "/welcome", request.url));
  }
  if (startsWithAny(pathname, BANK_PAGES) && !hasSession) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname);
    return NextResponse.redirect(login);
  }
  if (startsWithAny(pathname, GUEST_PAGES) && hasSession) {
    return NextResponse.redirect(new URL("/home", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Skip Next.js internals, our auth API and static files.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|icon.svg|apple-icon.png|icons|manifest.webmanifest|sw.js|offline.html).*)"],
};
