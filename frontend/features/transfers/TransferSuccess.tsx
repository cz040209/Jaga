"use client";

import { motion } from "framer-motion";
import { Home, ReceiptText, Repeat2 } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button-variants";
import { formatAmount } from "@/lib/format";
import type { Transfer } from "@/types";

/** Animated tick: the circle pops, then the check draws itself. */
function SuccessMark() {
  return (
    <div className="relative mx-auto size-28">
      {/* Two soft rings ripple outwards once. */}
      {[0, 0.15].map((delay) => (
        <motion.span
          key={delay}
          className="absolute inset-0 rounded-full bg-emerald-400/30"
          initial={{ scale: 0.6, opacity: 0.8 }}
          animate={{ scale: 1.9, opacity: 0 }}
          transition={{ duration: 1.1, delay: 0.25 + delay, ease: "easeOut" }}
        />
      ))}
      <motion.div
        className="absolute inset-0 grid place-items-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 shadow-[0_18px_40px_-12px_rgb(16_185_129/0.6)]"
        initial={{ scale: 0, rotate: -45 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 15 }}
      >
        <svg viewBox="0 0 52 52" className="size-14" fill="none">
          <motion.path
            d="M14 27.5 22.5 36 38.5 18"
            stroke="white"
            strokeWidth="5"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.45, delay: 0.3, ease: "easeOut" }}
          />
        </svg>
      </motion.div>
    </div>
  );
}

const rise = (delay: number) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { type: "spring" as const, stiffness: 260, damping: 26, delay },
});

export function TransferSuccess({ transfer, onAgain }: { transfer: Transfer; onAgain: () => void }) {
  const name = transfer.payee?.nickname ?? transfer.counterparty.name;
  return (
    <div className="flex min-h-[78dvh] flex-col justify-center pt-6 text-center">
      <SuccessMark />
      <motion.p {...rise(0.45)} className="mt-7 text-[15px] font-semibold text-emerald-600 dark:text-emerald-400">
        Money sent
      </motion.p>
      <motion.p {...rise(0.5)} className="mt-1 text-[44px] font-extrabold leading-none tracking-tight text-foreground tabular-nums">
        <span className="mr-1 text-[22px] text-muted-foreground">RM</span>
        {formatAmount(transfer.amount)}
      </motion.p>
      <motion.p {...rise(0.55)} className="mt-3 text-[15px] text-muted-foreground">
        to <span className="font-semibold text-foreground">{name}</span> · {transfer.counterparty.masked_number}
      </motion.p>
      <motion.p {...rise(0.6)} className="mt-2 text-[12.5px] font-medium tracking-wide text-muted-foreground/80">
        Ref {transfer.reference}
      </motion.p>

      <motion.div {...rise(0.7)} className="mt-10 space-y-3">
        <Link href={`/transfers/${transfer.id}`} className={buttonVariants({ size: "lg", className: "w-full" })}>
          <ReceiptText /> View receipt
        </Link>
        <div className="grid grid-cols-2 gap-3">
          <Link href="/home" className={buttonVariants({ size: "lg", variant: "outline" })}>
            <Home /> Home
          </Link>
          <button type="button" onClick={onAgain} className={buttonVariants({ size: "lg", variant: "outline" })}>
            <Repeat2 /> Send more
          </button>
        </div>
      </motion.div>
    </div>
  );
}
