/**
 * A stable ID for this browser/device (FingerprintJS, open-source version).
 * Sent as `device_fingerprint` on register/login so the backend can recognise
 * returning devices and flag new ones. The backend stores only a hash of it.
 */

import FingerprintJS from "@fingerprintjs/fingerprintjs";

let cached: Promise<string | null> | null = null;

export function getDeviceFingerprint(): Promise<string | null> {
  if (typeof window === "undefined") return Promise.resolve(null);
  cached ??= FingerprintJS.load()
    .then((agent) => agent.get())
    .then((result) => result.visitorId)
    .catch(() => null); // blocked by a privacy extension: the login still works
  return cached;
}
