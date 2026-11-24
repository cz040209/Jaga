"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Copy, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Skeleton } from "@/components/ui/skeleton";
import { useCountUp } from "@/features/accounts/useCountUp";
import { groupAccountNumber } from "@/lib/format";
import type { Account } from "@/types";

const HIDE_KEY = "jaga.hideBalance";

/** Remember the eye toggle on this device only. Storage can be blocked, so never trust it. */
function useHiddenBalance(): [boolean, () => void] {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    try {
      setHidden(localStorage.getItem(HIDE_KEY) === "1");
    } catch {
      /* private mode: just show it */
    }
  }, []);
  const toggle = () =>
    setHidden((value) => {
      try {
        localStorage.setItem(HIDE_KEY, value ? "0" : "1");
      } catch {
        /* ignore */
      }
      return !value;
    });
  return [hidden, toggle];
}

/** Slowly drifting light inside the card: the "aurora". */
function Aurora() {
  return (
    <div aria-hidden className="absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-teal-400 via-teal-500 to-cyan-600" />
      <motion.div
        className="absolute -right-20 -top-24 size-72 rounded-full bg-emerald-200/50 blur-3xl"
        animate={{ x: [0, -40, 0], y: [0, 30, 0], scale: [1, 1.15, 1] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -bottom-28 -left-16 size-72 rounded-full bg-sky-300/50 blur-3xl"
        animate={{ x: [0, 50, 0], y: [0, -20, 0], scale: [1, 1.1, 1] }}
        transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* Gentle diagonal sheen. */}
      <div className="absolute inset-0 bg-[linear-gradient(115deg,transparent_35%,rgb(255_255_255/0.18)_50%,transparent_65%)]" />
    </div>
  );
}

export function BalanceCard({ account }: { account: Account | undefined }) {
  const [hidden, toggleHidden] = useHiddenBalance();
  const animated = useCountUp(account?.balance);

  if (!account) return <Skeleton className="h-[200px] w-full rounded-[32px]" />;

  const [whole, cents] = (animated ?? "0.00").split(".");

  async function copyNumber() {
    try {
      await navigator.clipboard.writeText(account!.account_number);
      toast.success("Account number copied", {
        description: "Share it so friends can send you money.",
      });
    } catch {
      toast.error("Couldn't copy. Your number is " + groupAccountNumber(account!.account_number));
    }
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 220, damping: 26 }}
      className="relative isolate overflow-hidden rounded-[32px] p-6 text-white shadow-[0_24px_48px_-18px_rgb(13_148_136/0.55)]"
      aria-label="Account balance"
    >
      <Aurora />

      <div className="flex items-start justify-between">
        <div>
          <p className="text-[13px] font-medium text-white/80">Jaga Savings</p>
          <motion.button
            type="button"
            onClick={copyNumber}
            whileTap={{ scale: 0.95 }}
            className="mt-1.5 inline-flex items-center gap-1.5 rounded-full bg-white/20 px-3 py-1 text-[13px] font-semibold text-white ring-1 ring-white/30 backdrop-blur-md transition hover:bg-white/30"
            aria-label="Copy account number"
          >
            {account.masked_number}
            <Copy className="size-3.5" />
          </motion.button>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-white/20 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider ring-1 ring-white/30 backdrop-blur-md">
          <ShieldCheck className="size-3.5" /> Protected
        </span>
      </div>

      <div className="mt-9">
        <div className="flex items-center gap-1.5 text-[13px] font-medium text-white/80">
          Available balance
          <motion.button
            type="button"
            onClick={toggleHidden}
            whileTap={{ scale: 0.85, rotate: -8 }}
            className="rounded-full p-1 transition hover:bg-white/20"
            aria-label={hidden ? "Show balance" : "Hide balance"}
          >
            {hidden ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </motion.button>
        </div>
        <div className="mt-1 flex h-12 items-baseline gap-1.5 font-extrabold tracking-tight">
          <span className="text-lg text-white/85">RM</span>
          <AnimatePresence mode="wait" initial={false}>
            {hidden ? (
              <motion.span
                key="hidden"
                initial={{ opacity: 0, filter: "blur(6px)" }}
                animate={{ opacity: 1, filter: "blur(0px)" }}
                exit={{ opacity: 0, filter: "blur(6px)" }}
                transition={{ duration: 0.2 }}
                className="text-[42px] leading-none"
              >
                ••••••
              </motion.span>
            ) : (
              <motion.span
                key="shown"
                initial={{ opacity: 0, filter: "blur(6px)" }}
                animate={{ opacity: 1, filter: "blur(0px)" }}
                exit={{ opacity: 0, filter: "blur(6px)" }}
                transition={{ duration: 0.2 }}
                className="flex items-baseline"
              >
                <span className="text-[42px] leading-none tabular-nums">{whole}</span>
                <span className="text-xl text-white/85 tabular-nums">.{cents}</span>
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.section>
  );
}
