"use client";

import { ChevronRight, ShieldAlert, ShieldCheck } from "lucide-react";

import { Avatar } from "@/components/shared/Avatar";
import type { Payee } from "@/types";

/** Mule-check badge. "pending" (Phase 2 not built yet) shows nothing. */
export function CheckBadge({ status }: { status: Payee["check_status"] }) {
  if (status === "clear") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300">
        <ShieldCheck className="size-3" /> Checked
      </span>
    );
  }
  if (status === "watchlisted" || status === "blocked") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-700 dark:bg-rose-500/15 dark:text-rose-300">
        <ShieldAlert className="size-3" /> {status === "blocked" ? "Blocked" : "Reported"}
      </span>
    );
  }
  return null;
}

/** A payee as a tappable row: avatar, nickname, masked name and number. */
export function PayeeRow({ payee, onClick }: { payee: Payee; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="-mx-2 flex w-[calc(100%+16px)] items-center gap-3.5 rounded-2xl px-2 py-3 text-left transition-colors hover:bg-slate-900/[0.03] dark:hover:bg-white/[0.04]"
    >
      <Avatar name={payee.nickname} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-[15px] font-semibold text-foreground">{payee.nickname}</p>
          <CheckBadge status={payee.check_status} />
        </div>
        <p className="truncate text-[12.5px] text-muted-foreground">
          {payee.recipient.masked_name} · {payee.recipient.masked_number}
        </p>
      </div>
      <ChevronRight className="size-4 shrink-0 text-muted-foreground/60" />
    </button>
  );
}
