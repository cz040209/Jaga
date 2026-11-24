"use client";

import { motion } from "framer-motion";
import { BellRing, Check, Lock, ShieldAlert, Snowflake, Zap } from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/brand/Logo";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { buttonVariants } from "@/components/ui/button-variants";

const FEATURES = [
  { icon: Zap, title: "Scam checks in real time", text: "Every transfer is checked before it leaves.", chip: "from-teal-400 to-teal-600" },
  { icon: Snowflake, title: "Freeze in one tap", text: "Lock your account the moment something feels off.", chip: "from-sky-400 to-blue-500" },
  { icon: BellRing, title: "Alerts you'll actually see", text: "Know when money moves or a device logs in.", chip: "from-violet-400 to-indigo-500" },
];

const float = (delay: number) => ({
  animate: { y: [0, -8, 0] },
  transition: { duration: 5, repeat: Infinity, ease: "easeInOut" as const, delay },
});

/** Layered, gently floating preview of what Jaga does. */
function HeroPreview() {
  return (
    <div className="relative mx-auto h-[268px] w-full max-w-[330px]">
      {/* Balance card */}
      <motion.div
        initial={{ opacity: 0, y: 30, rotate: -8 }}
        animate={{ opacity: 1, y: 0, rotate: -6 }}
        transition={{ type: "spring", stiffness: 120, damping: 16 }}
        className="absolute left-1 top-6"
      >
        <motion.div
          {...float(0)}
          className="relative w-[250px] overflow-hidden rounded-[28px] bg-gradient-to-br from-teal-400 via-teal-500 to-cyan-600 p-5 text-white shadow-[0_24px_40px_-16px_rgb(13_148_136/0.6)]"
        >
          <div className="absolute -right-12 -top-12 size-36 rounded-full bg-emerald-200/50 blur-2xl" />
          <div className="absolute -bottom-14 -left-8 size-36 rounded-full bg-sky-300/50 blur-2xl" />
          <p className="relative text-[11px] font-semibold text-white/85">Jaga Savings · •••• 2011</p>
          <p className="relative mt-7 text-[11px] text-white/80">Available balance</p>
          <p className="relative text-[28px] font-extrabold tracking-tight">
            <span className="text-sm text-white/85">RM </span>10,000
            <span className="text-base text-white/85">.00</span>
          </p>
        </motion.div>
      </motion.div>

      {/* Scam alert */}
      <motion.div
        initial={{ opacity: 0, x: 40, y: 20 }}
        animate={{ opacity: 1, x: 0, y: 0 }}
        transition={{ type: "spring", stiffness: 140, damping: 16, delay: 0.25 }}
        className="absolute bottom-0 right-0"
      >
        <motion.div {...float(0.8)} className="glass w-[236px] rounded-3xl p-4 shadow-[var(--shadow-float)]">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-amber-300 to-orange-500 text-white shadow-md shadow-orange-500/30">
              <ShieldAlert className="size-5" />
            </span>
            <div>
              <p className="text-[13px] font-bold text-foreground">Transfer paused</p>
              <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                New payee + large amount. Is someone telling you to send this?
              </p>
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* Little badges */}
      <motion.span
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 14, delay: 0.5 }}
        className="absolute right-5 top-1"
      >
        <motion.span
          {...float(0.4)}
          className="glass grid size-12 place-items-center rounded-2xl text-teal-600 dark:text-teal-400 shadow-[var(--shadow-soft)]"
        >
          <Lock className="size-5" />
        </motion.span>
      </motion.span>
      <motion.span
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 14, delay: 0.65 }}
        className="absolute left-0 top-0"
      >
        <motion.span
          {...float(1.2)}
          className="grid size-9 place-items-center rounded-full bg-emerald-500 text-white shadow-lg shadow-emerald-500/40 ring-4 ring-white dark:ring-slate-900"
        >
          <Check className="size-4" strokeWidth={3} />
        </motion.span>
      </motion.span>
    </div>
  );
}

const rise = (delay: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { type: "spring" as const, stiffness: 220, damping: 26, delay },
});

export function Welcome() {
  return (
    <div className="flex min-h-dvh flex-col px-6 pb-[max(24px,env(safe-area-inset-bottom))] pt-[max(20px,env(safe-area-inset-top))]">
      <motion.div {...rise(0)} className="flex items-center justify-between">
        <Logo />
        <ThemeToggle className="size-11" />
      </motion.div>

      <div className="mt-8">
        <HeroPreview />
      </div>

      <motion.div {...rise(0.15)} className="mt-9">
        <h1 className="text-[34px] font-extrabold leading-[1.08] tracking-tight text-foreground">
          Banking that has
          <br />
          <span className="bg-gradient-to-r from-teal-500 via-cyan-500 to-sky-500 bg-clip-text text-transparent">
            your back.
          </span>
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground">
          Jaga watches every transfer for scams, so you can send money with peace of mind.
        </p>
      </motion.div>

      <ul className="mt-7 space-y-4">
        {FEATURES.map(({ icon: Icon, title, text, chip }, index) => (
          <motion.li key={title} {...rise(0.25 + index * 0.07)} className="flex items-center gap-3.5">
            <span
              className={`grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br text-white shadow-md ${chip}`}
            >
              <Icon className="size-5" />
            </span>
            <div>
              <p className="text-[14.5px] font-bold text-foreground">{title}</p>
              <p className="text-[13px] text-muted-foreground">{text}</p>
            </div>
          </motion.li>
        ))}
      </ul>

      <motion.div {...rise(0.5)} className="mt-auto space-y-3 pt-10">
        <Link href="/register" className={buttonVariants({ size: "lg", className: "w-full" })}>
          Create free account
        </Link>
        <Link
          href="/login"
          className={buttonVariants({ size: "lg", variant: "outline", className: "w-full" })}
        >
          I already have an account
        </Link>
        <p className="pt-1 text-center text-[12px] text-muted-foreground/80">
          Demo bank · play money only · no real funds
        </p>
      </motion.div>
    </div>
  );
}
