"use client";

import { motion } from "framer-motion";
import { ChevronRight, Inbox as EmptyIcon } from "lucide-react";
import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { useRecentTransactions } from "@/features/accounts/hooks";
import { TransactionRow } from "@/features/accounts/TransactionRow";

export function RecentActivity() {
  const { data, isPending, isError, refetch } = useRecentTransactions(5);

  return (
    <section className="glass rounded-[28px] p-5 shadow-[var(--shadow-soft)]">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-[17px] font-bold text-foreground">Recent activity</h2>
        <Link
          href="/history"
          className="inline-flex items-center gap-0.5 rounded-full px-2 py-1 text-[13px] font-semibold text-teal-600 transition hover:bg-teal-50 dark:text-teal-400 dark:hover:bg-teal-400/10"
        >
          See all <ChevronRight className="size-4" />
        </Link>
      </div>

      {isPending ? (
        <ul className="space-y-4 py-3">
          {[0, 1, 2].map((i) => (
            <li key={i} className="flex items-center gap-3.5">
              <Skeleton className="size-11 rounded-2xl" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-3 w-1/3" />
              </div>
              <Skeleton className="h-4 w-16" />
            </li>
          ))}
        </ul>
      ) : isError ? (
        <div className="py-8 text-center">
          <p className="text-sm text-muted-foreground">Couldn&apos;t load your activity.</p>
          <button onClick={() => refetch()} className="mt-2 text-sm font-semibold text-teal-600 dark:text-teal-400">
            Try again
          </button>
        </div>
      ) : data.items.length === 0 ? (
        <div className="flex flex-col items-center py-8 text-center">
          <EmptyIcon className="size-8 text-muted-foreground/50" />
          <p className="mt-2 text-sm text-muted-foreground">No activity yet.</p>
        </div>
      ) : (
        <motion.ul
          initial="hidden"
          animate="show"
          variants={{ show: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } } }}
        >
          {data.items.map((line) => (
            <motion.li
              key={line.id}
              variants={{
                hidden: { opacity: 0, y: 10 },
                show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 26 } },
              }}
            >
              <TransactionRow line={line} />
            </motion.li>
          ))}
        </motion.ul>
      )}
    </section>
  );
}
