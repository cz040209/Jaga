"use client";

import { useEffect } from "react";

/**
 * Registers public/sw.js (the offline page). Browsers only allow service
 * workers on https:// or localhost, so on http://192.168... it's skipped.
 */
export function ServiceWorker() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => {
      /* not fatal: the app works without it */
    });
  }, []);
  return null;
}
