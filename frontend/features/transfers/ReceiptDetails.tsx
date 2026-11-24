"use client";

import { Copy } from "lucide-react";
import { toast } from "sonner";

import { formatDateTime, formatRM } from "@/lib/format";
import type { Transfer } from "@/types";

const STATUS: Record<string, { label: string; className: string }> = {
  posted: { label: "Successful", className: "bg-emerald-50 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300" },
  pending: { label: "Processing", className: "bg-sky-50 text-sky-700 dark:bg-sky-400/15 dark:text-sky-300" },
  held: { label: "On hold", className: "bg-amber-50 text-amber-700 dark:bg-amber-400/15 dark:text-amber-300" },
  step_up_required: { label: "Needs confirmation", className: "bg-amber-50 text-amber-700 dark:bg-amber-400/15 dark:text-amber-300" },
  blocked: { label: "Blocked", className: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
  failed: { label: "Failed", className: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
  reversed: { label: "Reversed", className: "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-300" },
  cancelled: { label: "Cancelled", className: "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-300" },
};

export function StatusPill({ status }: { status: string }) {
  const look = STATUS[status] ?? STATUS.pending;
  return <span className={`rounded-full px-2.5 py-1 text-[12px] font-bold ${look.className}`}>{look.label}</span>;
}

/** The receipt lines: who, which accounts, reference (copyable), time, note. */
export function ReceiptDetails({ transfer }: { transfer: Transfer }) {
  const out = transfer.direction === "out";
  const rows: { label: string; value: React.ReactNode }[] = [
    { label: "Status", value: <StatusPill status={transfer.status} /> },
    {
      label: out ? "To" : "From",
      value: (
        <>
          {transfer.payee?.nickname && transfer.payee.nickname !== transfer.counterparty.name && (
            <span className="block">{transfer.payee.nickname}</span>
          )}
          <span className="block">{transfer.counterparty.name}</span>
          <span className="block font-normal text-muted-foreground">{transfer.counterparty.masked_number}</span>
        </>
      ),
    },
    { label: out ? "From" : "To", value: `Jaga Savings ${transfer.from_account}` },
    { label: "Date", value: formatDateTime(transfer.posted_at) },
    ...(transfer.note ? [{ label: "Note", value: transfer.note }] : []),
    {
      label: "Reference",
      value: (
        <button
          type="button"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(transfer.reference);
              toast.success("Reference copied");
            } catch {
              /* clipboard blocked: the reference is on screen anyway */
            }
          }}
          className="inline-flex items-center gap-1.5 text-[13px] tracking-wide hover:text-teal-600 dark:hover:text-teal-400"
        >
          {transfer.reference} <Copy className="size-3.5" />
        </button>
      ),
    },
    { label: "Balance after", value: formatRM(transfer.balance_after) },
  ];

  return (
    <dl className="divide-y divide-border/70">
      {rows.map((row) => (
        <div key={row.label} className="flex items-start justify-between gap-4 py-3.5 text-[14px]">
          <dt className="shrink-0 text-muted-foreground">{row.label}</dt>
          <dd className="min-w-0 break-words text-right font-semibold text-foreground">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}
