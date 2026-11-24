"use client";

import { animate, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

import { formatAmount } from "@/lib/format";

/**
 * Animates a money string from 0 up to its value ("10000.00"), for display only.
 * The animation uses a number in between, but the FINAL text is always the
 * exact string from the API, so no rounding ever reaches the screen at rest.
 */
export function useCountUp(amount: string | undefined, duration = 1.1): string | undefined {
  const reduceMotion = useReducedMotion();
  const [text, setText] = useState<string | undefined>(
    amount && reduceMotion ? formatAmount(amount) : undefined,
  );

  useEffect(() => {
    if (amount === undefined) return;
    if (reduceMotion) {
      setText(formatAmount(amount));
      return;
    }
    const controls = animate(0, Number(amount), {
      duration,
      ease: [0.16, 1, 0.3, 1], // fast start, gentle landing
      onUpdate: (value) => setText(formatAmount(value.toFixed(2))),
      onComplete: () => setText(formatAmount(amount)),
    });
    return () => controls.stop();
  }, [amount, duration, reduceMotion]);

  return text;
}
