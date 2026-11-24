"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ReceiptText } from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState, LoadError } from "@/components/shared/EmptyState";
import { LoadMore } from "@/components/shared/LoadMore";
import { PageHeader } from "@/components/shared/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { useTransactionHistory } from "@/features/accounts/hooks";
import { TransactionRow } from "@/features/accounts/TransactionRow";
import { formatDay, sameDay } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Transaction } from "@/types";

const FILTERS = [
  { value: "all", label: "All" },
  { value: "in", label: "Money in" },
  { value: "out", label: "Money out" },
] as const;
type Filter = (typeof FILTERS)[number]["value"];

/** Group statement lines under day headings (Malaysia time). */
function groupByDay(lines: Transaction[]) {
  const groups: { day: string; lines: Transaction[] }[] = [];
  for (const line of lines) {
    const last = groups[groups.length - 1];
    if (last && sameDay(last.lines[0].posted_at, line.posted_at)) last.lines.push(line);
    else groups.push({ day: formatDay(line.posted_at), lines: [line] });
  }
  return groups;
}

function FilterChips({ value, onChange }: { value: Filter; onChange: (value: Filter) => void }) {
  return (
    <div role="tablist" aria-label="Filter" className="glass flex gap-1 rounded-full p-1 shadow-[var(--shadow-soft)]">
      {FILTERS.map((filter) => {
        const selected = filter.value === value;
        return (
          <button
            key={filter.value}
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(filter.value)}
            className={cn(
              "relative h-10 flex-1 rounded-full text-[13.5px] font-semibold transition-colors",
              selected ? "text-white" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {selected && (
              <motion.span
                layoutId="history-filter"
                className="absolute inset-0 rounded-full bg-gradient-to-b from-teal-500 to-teal-600 shadow-[var(--shadow-glow)]"
                transition={{ type: "spring", stiffness: 450, damping: 34 }}
              />
            )}
            <span className="relative">{filter.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export function HistoryScreen() {
  const [filter, setFilter] = useState<Filter>("all");
  const { data, isPending, isError, refetch, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useTransactionHistory();

  const groups = useMemo(() => {
    const lines = data?.pages.flatMap((page) => page.items) ?? [];
    return groupByDay(filter === "all" ? lines : lines.filter((line) => line.direction === filter));
  }, [data, filter]);

  return (
    <div>
      <PageHeader title="History" subtitle="Every ringgit in and out of your account." />
      <FilterChips value={filter} onChange={setFilter} />

      <div className="mt-5">
        {isPending ? (
          <div className="glass space-y-4 rounded-[28px] p-5 shadow-[var(--shadow-soft)]">
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center gap-3.5">
                <Skeleton className="size-11 rounded-2xl" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <LoadError what="your history" onRetry={() => refetch()} />
        ) : groups.length === 0 ? (
          <EmptyState
            icon={ReceiptText}
            title={filter === "all" ? "No transactions yet" : "Nothing here yet"}
            description={
              filter === "all"
                ? "Money you send and receive will show up here."
                : `No ${filter === "in" ? "incoming" : "outgoing"} money in what's loaded so far.`
            }
          />
        ) : (
          <AnimatePresence mode="popLayout" initial={false}>
            <motion.div
              key={filter}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {groups.map((group) => (
                <section key={group.day} className="glass rounded-[28px] px-5 pb-2 pt-4 shadow-[var(--shadow-soft)]">
                  <h2 className="text-[12px] font-bold uppercase tracking-wider text-muted-foreground">
                    {group.day}
                  </h2>
                  <ul>
                    {group.lines.map((line) => (
                      <li key={line.id}>
                        <TransactionRow line={line} timeOnly />
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </motion.div>
          </AnimatePresence>
        )}
        {!isPending && !isError && (data?.pages[0]?.items.length ?? 0) > 0 && (
          <LoadMore hasMore={!!hasNextPage} loading={isFetchingNextPage} onLoadMore={() => fetchNextPage()} />
        )}
      </div>
    </div>
  );
}
