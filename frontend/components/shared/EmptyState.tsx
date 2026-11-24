"use client";

import { motion } from "framer-motion";

/** Friendly "nothing here yet" block with a floating icon. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <motion.span
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        className="grid size-16 place-items-center rounded-3xl bg-gradient-to-br from-teal-50 to-sky-50 text-teal-600 ring-1 ring-teal-100 dark:from-teal-500/15 dark:to-sky-500/10 dark:text-teal-300 dark:ring-teal-400/20"
      >
        <Icon className="size-7" />
      </motion.span>
      <p className="mt-4 text-[16px] font-bold text-foreground">{title}</p>
      <p className="mt-1 max-w-[260px] text-[13.5px] leading-relaxed text-muted-foreground">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/** Small "couldn't load" block with a retry. */
export function LoadError({ what, onRetry }: { what: string; onRetry: () => void }) {
  return (
    <div className="py-10 text-center">
      <p className="text-sm text-muted-foreground">Couldn&apos;t load {what}.</p>
      <button onClick={onRetry} className="mt-2 text-sm font-semibold text-teal-600 dark:text-teal-400">
        Try again
      </button>
    </div>
  );
}
