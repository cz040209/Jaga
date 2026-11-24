"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

/** A calm, rotating reminder. Real scam advice, matching Jaga's purpose. */
const TIPS = [
  "Jaga will never ask for your password or codes, not even by phone.",
  "Police, LHDN and Bank Negara will never ask you to move money to a \"safe account\".",
  "In doubt about a message? Forward it to Jaga to check if it's a scam.",
  "Someone pressuring you to transfer right now? Stop, hang up, and call 997.",
];

export function SafetyTip() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    // Random start after mount (no server/client mismatch), then a new tip every 8 s.
    setIndex(Math.floor(Math.random() * TIPS.length));
    const timer = setInterval(() => setIndex((i) => (i + 1) % TIPS.length), 8000);
    return () => clearInterval(timer);
  }, []);

  return (
    <aside className="relative flex gap-3.5 overflow-hidden rounded-[24px] bg-gradient-to-r from-teal-50 to-sky-50 p-4 ring-1 ring-teal-100 dark:from-teal-500/10 dark:to-sky-500/10 dark:ring-teal-400/15">
      <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-white text-teal-600 shadow-sm dark:bg-slate-900/70 dark:text-teal-300">
        <ShieldCheck className="size-5" />
      </span>
      <div className="min-h-[52px] flex-1">
        <p className="text-[13px] font-bold text-teal-900 dark:text-teal-200">Jaga safety tip</p>
        <AnimatePresence mode="wait">
          <motion.p
            key={index}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.3 }}
            className="mt-0.5 text-[13px] leading-relaxed text-teal-900/75 dark:text-teal-100/70"
          >
            {TIPS[index]}
          </motion.p>
        </AnimatePresence>
      </div>
    </aside>
  );
}
