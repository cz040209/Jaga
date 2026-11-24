"use client";

import { ArrowDownLeft, ArrowUpRight, Gift } from "lucide-react";
import Link from "next/link";

import { formatAmount, formatWhen } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Transaction } from "@/types";

function look(line: Transaction) {
  if (line.type === "opening_balance") {
    return {
      Icon: Gift,
      chip: "bg-amber-100 text-amber-600 dark:bg-amber-400/15 dark:text-amber-300",
      title: "Welcome bonus",
    };
  }
  if (line.direction === "in") {
    return {
      Icon: ArrowDownLeft,
      chip: "bg-emerald-100 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300",
      title: `From ${line.counterparty.name}`,
    };
  }
  return {
    Icon: ArrowUpRight,
    chip: "bg-slate-100 text-slate-600 dark:bg-white/[0.07] dark:text-slate-300",
    title: `To ${line.counterparty.name}`,
  };
}

/**
 * One statement line: icon, who, note, amount and time.
 * Transfers open their receipt; other lines (welcome bonus) are plain.
 */
export function TransactionRow({ line, timeOnly = false }: { line: Transaction; timeOnly?: boolean }) {
  const { Icon, chip, title } = look(line);
  const incoming = line.direction === "in";
  const when = formatWhen(line.posted_at);

  const body = (
    <>
      <span className={cn("grid size-11 shrink-0 place-items-center rounded-2xl", chip)}>
        <Icon className="size-5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[15px] font-semibold text-foreground">{title}</p>
        <p className="truncate text-[12.5px] text-muted-foreground">{line.description ?? "Fund transfer"}</p>
      </div>
      <div className="shrink-0 text-right">
        <p
          className={cn(
            "text-[15px] font-bold tabular-nums",
            incoming ? "text-emerald-600 dark:text-emerald-400" : "text-foreground",
          )}
        >
          {incoming ? "+" : "−"}
          {formatAmount(line.amount)}
        </p>
        <p className="text-[12px] text-muted-foreground/80">
          {timeOnly ? when.replace(/^(Today|Yesterday|[^,]+), /, "") : when}
        </p>
      </div>
    </>
  );

  const rowClass =
    "-mx-2 flex items-center gap-3.5 rounded-2xl px-2 py-3 transition-colors hover:bg-slate-900/[0.03] dark:hover:bg-white/[0.04]";

  return line.type === "transfer" ? (
    <Link href={`/transfers/${line.transaction_id}`} className={rowClass}>
      {body}
    </Link>
  ) : (
    <div className={rowClass}>{body}</div>
  );
}
