"use client";

import { motion } from "framer-motion";
import { ArrowDownLeft, ArrowUpRight, Share2 } from "lucide-react";
import { toast } from "sonner";

import { LoadError } from "@/components/shared/EmptyState";
import { PageHeader } from "@/components/shared/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { useTransfer } from "@/features/transfers/hooks";
import { ReceiptDetails } from "@/features/transfers/ReceiptDetails";
import { ApiError } from "@/lib/api/errors";
import { formatAmount, formatDateTime, formatRM } from "@/lib/format";
import { cn } from "@/lib/utils";

export function ReceiptScreen({ id }: { id: number }) {
  const { data: transfer, isPending, isError, error, refetch } = useTransfer(id);

  async function share() {
    if (!transfer) return;
    const text = `Jaga transfer ${transfer.reference}: ${formatRM(transfer.amount)} ${
      transfer.direction === "out" ? "to" : "from"
    } ${transfer.counterparty.name} on ${formatDateTime(transfer.posted_at)}.`;
    try {
      if (navigator.share) await navigator.share({ title: "Jaga receipt", text });
      else {
        await navigator.clipboard.writeText(text);
        toast.success("Receipt copied");
      }
    } catch {
      /* share sheet dismissed */
    }
  }

  return (
    <div>
      <PageHeader back="history" title="Receipt" />

      {isPending ? (
        <Skeleton className="h-[460px] w-full rounded-[32px]" />
      ) : isError ? (
        error instanceof ApiError && error.status === 404 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">This receipt doesn&apos;t exist.</p>
        ) : (
          <LoadError what="this receipt" onRetry={() => refetch()} />
        )
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 26 }}
          className="glass relative overflow-hidden rounded-[32px] shadow-[var(--shadow-float)]"
        >
          <div className="px-6 pb-5 pt-7 text-center">
            <span
              className={cn(
                "mx-auto grid size-14 place-items-center rounded-2xl",
                transfer.direction === "in"
                  ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300"
                  : "bg-teal-100 text-teal-700 dark:bg-teal-400/15 dark:text-teal-300",
              )}
            >
              {transfer.direction === "in" ? <ArrowDownLeft className="size-7" /> : <ArrowUpRight className="size-7" />}
            </span>
            <p className="mt-3 text-[14px] font-medium text-muted-foreground">
              {transfer.direction === "in" ? "Money received" : "Money sent"}
            </p>
            <p
              className={cn(
                "mt-1 text-[40px] font-extrabold leading-none tracking-tight tabular-nums",
                transfer.direction === "in" ? "text-emerald-600 dark:text-emerald-400" : "text-foreground",
              )}
            >
              <span className="mr-1 text-[20px] text-muted-foreground">RM</span>
              {formatAmount(transfer.amount)}
            </p>
          </div>

          {/* Ticket-style perforation between the amount and the details. */}
          <div className="relative flex items-center" aria-hidden>
            <span className="absolute -left-3 size-6 rounded-full bg-background" />
            <span className="mx-5 w-full border-t-2 border-dashed border-border" />
            <span className="absolute -right-3 size-6 rounded-full bg-background" />
          </div>

          <div className="px-6 pb-2 pt-2">
            <ReceiptDetails transfer={transfer} />
          </div>
          <div className="px-6 pb-6">
            <button
              type="button"
              onClick={share}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-muted text-[14px] font-semibold text-foreground transition hover:bg-muted/70"
            >
              <Share2 className="size-4" /> Share receipt
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
