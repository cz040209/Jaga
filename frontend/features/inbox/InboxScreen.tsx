"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDownLeft,
  ArrowUpRight,
  CheckCheck,
  ChevronRight,
  KeyRound,
  MailOpen,
  Smartphone,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { EmptyState, LoadError } from "@/components/shared/EmptyState";
import { LoadMore } from "@/components/shared/LoadMore";
import { PageHeader } from "@/components/shared/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { useInbox, useMarkAllRead, useMarkRead } from "@/features/inbox/hooks";
import { formatDay, formatWhen, sameDay } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { InboxMessage } from "@/types";

/** Icon and colour per kind of message (the backend's template key). */
const LOOKS: Record<string, { icon: typeof Sparkles; chip: string }> = {
  transfer_received: { icon: ArrowDownLeft, chip: "from-emerald-400 to-teal-600" },
  transfer_sent: { icon: ArrowUpRight, chip: "from-teal-400 to-cyan-600" },
  new_device_login: { icon: Smartphone, chip: "from-amber-300 to-orange-500" },
  password_changed: { icon: KeyRound, chip: "from-violet-400 to-indigo-500" },
  welcome: { icon: Sparkles, chip: "from-sky-400 to-blue-500" },
};
const DEFAULT_LOOK = { icon: MailOpen, chip: "from-slate-400 to-slate-600" };

function Message({ message, open, onToggle }: { message: InboxMessage; open: boolean; onToggle: () => void }) {
  const { icon: Icon, chip } = LOOKS[message.event ?? ""] ?? DEFAULT_LOOK;
  return (
    <motion.li layout="position" className="-mx-2">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full gap-3.5 rounded-2xl px-2 py-3 text-left transition-colors hover:bg-slate-900/[0.03] dark:hover:bg-white/[0.04]"
      >
        <span className={cn("grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br text-white shadow-sm", chip)}>
          <Icon className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className={cn("min-w-0 flex-1 truncate text-[15px] text-foreground", message.read ? "font-semibold" : "font-bold")}>
              {message.subject ?? "Jaga"}
            </p>
            <span className="shrink-0 text-[12px] text-muted-foreground/80">
              {formatWhen(message.received_at).replace(/^(Today|Yesterday|[^,]+), /, "")}
            </span>
            <AnimatePresence>
              {!message.read && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0 }}
                  className="size-2.5 shrink-0 rounded-full bg-teal-500 shadow-[0_0_0_4px_rgb(20_184_166/0.15)]"
                  aria-label="Unread"
                />
              )}
            </AnimatePresence>
          </div>
          <p className={cn("mt-0.5 text-[13.5px] leading-relaxed", open ? "whitespace-pre-line" : "line-clamp-2", message.read ? "text-muted-foreground" : "text-foreground/80")}>
            {message.message}
          </p>
        </div>
      </button>
      <AnimatePresence initial={false}>
        {open && message.transaction_id && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden pl-[64px]"
          >
            <Link
              href={`/transfers/${message.transaction_id}`}
              className="mb-3 inline-flex items-center gap-1 rounded-full bg-teal-50 px-3.5 py-2 text-[13px] font-semibold text-teal-700 transition hover:bg-teal-100 dark:bg-teal-400/10 dark:text-teal-300 dark:hover:bg-teal-400/20"
            >
              View receipt <ChevronRight className="size-4" />
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
}

export function InboxScreen() {
  const { data, isPending, isError, refetch, hasNextPage, fetchNextPage, isFetchingNextPage } = useInbox();
  const markRead = useMarkRead();
  const markAll = useMarkAllRead();
  const [openId, setOpenId] = useState<number | null>(null);

  const unread = data?.pages[0]?.unread_count ?? 0;
  const groups = useMemo(() => {
    const result: { day: string; items: InboxMessage[] }[] = [];
    for (const message of data?.pages.flatMap((page) => page.items) ?? []) {
      const last = result[result.length - 1];
      if (last && sameDay(last.items[0].received_at, message.received_at)) last.items.push(message);
      else result.push({ day: formatDay(message.received_at), items: [message] });
    }
    return result;
  }, [data]);

  function toggle(message: InboxMessage) {
    setOpenId((current) => (current === message.id ? null : message.id));
    if (!message.read) markRead.mutate(message.id);
  }

  return (
    <div>
      <PageHeader
        title="Inbox"
        subtitle={unread ? `${unread} unread message${unread === 1 ? "" : "s"}` : "Alerts and messages from Jaga."}
        action={
          <AnimatePresence>
            {unread > 0 && (
              <motion.button
                type="button"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                whileTap={{ scale: 0.94 }}
                onClick={() => markAll.mutate()}
                className="glass inline-flex h-10 items-center gap-1.5 rounded-full px-4 text-[13px] font-semibold text-teal-700 shadow-[var(--shadow-soft)] dark:text-teal-300"
              >
                <CheckCheck className="size-4" /> Mark all read
              </motion.button>
            )}
          </AnimatePresence>
        }
      />

      {isPending ? (
        <div className="glass space-y-5 rounded-[28px] p-5 shadow-[var(--shadow-soft)]">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="flex gap-3.5">
              <Skeleton className="size-11 rounded-2xl" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-4/5" />
              </div>
            </div>
          ))}
        </div>
      ) : isError ? (
        <LoadError what="your messages" onRetry={() => refetch()} />
      ) : groups.length === 0 ? (
        <div className="glass rounded-[28px] shadow-[var(--shadow-soft)]">
          <EmptyState icon={MailOpen} title="No messages" description="Transfer alerts and security notices will appear here." />
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map((group, index) => (
            <motion.section
              key={group.day}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", stiffness: 260, damping: 28, delay: Math.min(index, 4) * 0.05 }}
              className="glass rounded-[28px] px-5 pb-2 pt-4 shadow-[var(--shadow-soft)]"
            >
              <h2 className="text-[12px] font-bold uppercase tracking-wider text-muted-foreground">{group.day}</h2>
              <ul>
                {group.items.map((message) => (
                  <Message key={message.id} message={message} open={openId === message.id} onToggle={() => toggle(message)} />
                ))}
              </ul>
            </motion.section>
          ))}
          <LoadMore hasMore={!!hasNextPage} loading={isFetchingNextPage} onLoadMore={() => fetchNextPage()} endText="No older messages" />
        </div>
      )}
    </div>
  );
}
