"use client";

import { AnimatePresence, motion } from "framer-motion";
import { WifiOff } from "lucide-react";
import { useSyncExternalStore } from "react";

function subscribe(onChange: () => void) {
  window.addEventListener("online", onChange);
  window.addEventListener("offline", onChange);
  return () => {
    window.removeEventListener("online", onChange);
    window.removeEventListener("offline", onChange);
  };
}

/** A small pill that drops in when the phone loses its connection, inside the app. */
export function OfflineBanner() {
  const online = useSyncExternalStore(
    subscribe,
    () => navigator.onLine,
    () => true, // on the server, assume online
  );

  return (
    <AnimatePresence>
      {!online && (
        <motion.div
          role="status"
          initial={{ y: -60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -60, opacity: 0 }}
          transition={{ type: "spring", stiffness: 380, damping: 30 }}
          className="fixed inset-x-0 top-[max(12px,env(safe-area-inset-top))] z-[60] mx-auto flex w-max items-center gap-2 rounded-full bg-slate-900 px-4 py-2.5 text-[13px] font-semibold text-white shadow-[var(--shadow-float)] dark:bg-white dark:text-slate-900"
        >
          <WifiOff className="size-4" /> You&apos;re offline. Reconnecting…
        </motion.div>
      )}
    </AnimatePresence>
  );
}
