"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { LogoMark } from "@/components/brand/Logo";
import { ThemeToggle } from "@/components/theme/ThemeToggle";

/** Shared frame for login and register: back link, mark, title, then the form on a glass card. */
export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col px-5 pb-8 pt-[max(16px,env(safe-area-inset-top))]">
      <div className="flex items-center justify-between">
        <Link
          href="/welcome"
          className="glass -ml-1 inline-flex size-11 items-center justify-center rounded-full text-foreground/70 shadow-[var(--shadow-soft)] transition hover:text-foreground"
          aria-label="Back"
        >
          <ArrowLeft className="size-5" />
        </Link>
        <ThemeToggle className="size-11" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 240, damping: 28 }}
        className="mt-6 px-1"
      >
        <motion.div
          initial={{ scale: 0.6, rotate: -12, opacity: 0 }}
          animate={{ scale: 1, rotate: 0, opacity: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 16, delay: 0.05 }}
          className="inline-block"
        >
          <LogoMark className="size-12 drop-shadow-[0_8px_16px_rgb(13_148_136/0.35)]" />
        </motion.div>
        <h1 className="mt-4 text-[30px] font-extrabold leading-tight tracking-tight text-foreground">
          {title}
        </h1>
        <p className="mt-1.5 text-[15px] leading-relaxed text-muted-foreground">{subtitle}</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 220, damping: 28, delay: 0.08 }}
        className="glass mt-6 rounded-[32px] p-5 shadow-[var(--shadow-float)]"
      >
        {children}
      </motion.div>

      <div className="mt-6 text-center text-[14px] text-muted-foreground">{footer}</div>
    </div>
  );
}

/** Red banner for errors that aren't about one field ("Invalid email or password"). */
export function FormAlert({ message }: { message: string | null }) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, height: 0, x: 0 }}
          animate={{ opacity: 1, height: "auto", x: [0, -6, 6, -3, 3, 0] }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.35 }}
          role="alert"
          className="overflow-hidden"
        >
          <div className="rounded-2xl bg-rose-50 px-4 py-3 text-[14px] font-medium text-rose-700 ring-1 ring-rose-100 dark:bg-rose-500/15 dark:text-rose-300 dark:ring-rose-500/25">
            {message}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
