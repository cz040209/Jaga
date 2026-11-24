"use client";

import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { Fingerprint, Loader2 } from "lucide-react";
import { useRef, useState } from "react";

const HOLD_SECONDS = 1.1;

/**
 * "Hold to send": the button fills while pressed and only fires when full.
 * A deliberate gesture: harder to send money by accident, or in a rush
 * while a scammer is on the phone. Works with Enter/Space too.
 */
export function HoldToSend({
  label,
  onConfirm,
  busy = false,
  disabled = false,
}: {
  label: string;
  onConfirm: () => void;
  busy?: boolean;
  disabled?: boolean;
}) {
  const progress = useMotionValue(0);
  const scaleX = useTransform(progress, [0, 1], [0, 1]);
  const [holding, setHolding] = useState(false);
  const control = useRef<ReturnType<typeof animate> | null>(null);

  function start() {
    if (busy || disabled || holding) return;
    setHolding(true);
    control.current?.stop();
    control.current = animate(progress, 1, {
      duration: HOLD_SECONDS * (1 - progress.get()),
      ease: "linear",
      onComplete: () => {
        setHolding(false);
        navigator.vibrate?.(30);
        onConfirm();
        animate(progress, 0, { duration: 0.4, delay: 0.3 });
      },
    });
  }

  function cancel() {
    if (!holding) return;
    setHolding(false);
    control.current?.stop();
    control.current = animate(progress, 0, { type: "spring", stiffness: 300, damping: 30 });
  }

  return (
    <motion.button
      type="button"
      disabled={disabled || busy}
      whileTap={{ scale: 0.98 }}
      onPointerDown={start}
      onPointerUp={cancel}
      onPointerLeave={cancel}
      onPointerCancel={cancel}
      onContextMenu={(event) => event.preventDefault()}
      onKeyDown={(event) => {
        if ((event.key === "Enter" || event.key === " ") && !event.repeat) {
          event.preventDefault();
          start();
        }
      }}
      onKeyUp={(event) => (event.key === "Enter" || event.key === " ") && cancel()}
      className="relative isolate flex h-16 w-full touch-none select-none items-center justify-center gap-2.5 overflow-hidden rounded-full bg-gradient-to-b from-teal-500 to-teal-600 text-[16px] font-bold text-white shadow-[var(--shadow-glow)] outline-none focus-visible:ring-4 focus-visible:ring-ring/30 disabled:opacity-60"
    >
      {/* The fill that grows while holding. */}
      <motion.span
        aria-hidden
        style={{ scaleX, transformOrigin: "left" }}
        className="absolute inset-0 -z-10 bg-gradient-to-r from-emerald-400 to-teal-400"
      />
      {busy ? <Loader2 className="size-5 animate-spin" /> : <Fingerprint className="size-5" />}
      <span>{busy ? "Sending…" : holding ? "Keep holding…" : label}</span>
    </motion.button>
  );
}
