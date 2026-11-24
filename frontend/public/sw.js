/*
 * Jaga service worker. Deliberately minimal and safe for a bank:
 *
 *   - Bank data (/api/...) is NEVER cached: balances, transfers and messages
 *     always come fresh from the server, or not at all.
 *   - Pages are always loaded from the network. Only when the network fails
 *     do we show a friendly offline page (cached when the worker installs).
 *
 * Bump VERSION when offline.html changes, so phones pick up the new copy.
 */
const VERSION = "jaga-v1";
const OFFLINE_URL = "/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.add(new Request(OFFLINE_URL, { cache: "reload" }))));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // Remove caches from older versions.
      const keys = await caches.keys();
      await Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key)));
      // Start fetching pages while the worker boots (faster, no extra delay).
      if (self.registration.navigationPreload) await self.registration.navigationPreload.enable();
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  // Only page loads. Everything else (API calls, scripts, images) is left
  // alone and goes straight to the network as if there were no worker.
  if (event.request.mode !== "navigate") return;

  event.respondWith(
    (async () => {
      try {
        const preloaded = await event.preloadResponse;
        if (preloaded) return preloaded;
        return await fetch(event.request);
      } catch {
        const cache = await caches.open(VERSION);
        return (await cache.match(OFFLINE_URL)) ?? Response.error();
      }
    })(),
  );
});
