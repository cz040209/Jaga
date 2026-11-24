/**
 * The access token lives ONLY in memory (this module), never in localStorage.
 *
 * - A malicious script can't read it from storage.
 * - It's short-lived (15 min); when it's missing or expired we ask our own
 *   server (/api/auth/refresh) for a new one. The 30-day refresh token sits in
 *   an httpOnly cookie that JavaScript can't read at all.
 *
 * Listeners let the AuthProvider react when the session ends (e.g. a refresh fails).
 */

type Listener = (token: string | null) => void;

let accessToken: string | null = null;
const listeners = new Set<Listener>();

export const tokenStore = {
  get(): string | null {
    return accessToken;
  },
  set(token: string | null): void {
    accessToken = token;
    listeners.forEach((listener) => listener(token));
  },
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
