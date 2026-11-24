"use client";

import { motion } from "framer-motion";
import { Bell } from "lucide-react";
import Link from "next/link";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Skeleton } from "@/components/ui/skeleton";
import { BalanceCard } from "@/features/accounts/BalanceCard";
import { usePrimaryAccount } from "@/features/accounts/hooks";
import { QuickActions } from "@/features/accounts/QuickActions";
import { RecentActivity } from "@/features/accounts/RecentActivity";
import { SafetyTip } from "@/features/accounts/SafetyTip";
import { useUnreadCount } from "@/features/inbox/hooks";
import { useProfile } from "@/features/profile/hooks";
import { firstName, greeting, initials } from "@/lib/format";

function Header() {
  const { data: profile } = useProfile();
  const unread = useUnreadCount();

  return (
    <header className="flex items-center justify-between">
      <Link href="/profile" className="flex items-center gap-3">
        <span className="grid size-12 place-items-center rounded-full bg-gradient-to-br from-teal-300 to-teal-600 text-[15px] font-bold text-white shadow-[var(--shadow-glow)] ring-4 ring-white dark:ring-slate-800">
          {profile ? initials(profile.full_name) : ""}
        </span>
        <div>
          <p className="text-[13px] font-medium text-muted-foreground">{greeting()} 👋</p>
          {profile ? (
            <p className="text-[18px] font-extrabold tracking-tight text-foreground">
              {firstName(profile.full_name)}
            </p>
          ) : (
            <Skeleton className="mt-1 h-5 w-24" />
          )}
        </div>
      </Link>
      <div className="flex items-center gap-2.5">
        <ThemeToggle />
        <Link
          href="/inbox"
          aria-label={unread ? `Inbox, ${unread} unread` : "Inbox"}
          className="glass relative grid size-12 place-items-center rounded-full text-foreground/70 shadow-[var(--shadow-soft)] transition hover:text-foreground"
        >
          <motion.span
            // A tiny "ring" when there's something new.
            animate={unread > 0 ? { rotate: [0, -14, 12, -8, 0] } : { rotate: 0 }}
            transition={{ duration: 0.8, repeat: unread > 0 ? Infinity : 0, repeatDelay: 4 }}
          >
            <Bell className="size-5" />
          </motion.span>
          {unread > 0 && (
            <span className="absolute right-3 top-3 size-2.5 rounded-full bg-rose-500 ring-2 ring-white dark:ring-slate-900" />
          )}
        </Link>
      </div>
    </header>
  );
}

/** Each section rises in, one after another. */
const section = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 260, damping: 28 } },
};

export function HomeScreen() {
  const { account, isError, refetch } = usePrimaryAccount();

  return (
    <motion.div
      className="space-y-5"
      initial="hidden"
      animate="show"
      variants={{ show: { transition: { staggerChildren: 0.07 } } }}
    >
      <motion.div variants={section}>
        <Header />
      </motion.div>
      <motion.div variants={section}>
        {isError ? (
          <div className="glass rounded-[32px] p-6 text-center shadow-[var(--shadow-soft)]">
            <p className="text-sm text-muted-foreground">We couldn&apos;t load your balance.</p>
            <button onClick={() => refetch()} className="mt-2 text-sm font-semibold text-teal-600 dark:text-teal-400">
              Try again
            </button>
          </div>
        ) : (
          <BalanceCard account={account} />
        )}
      </motion.div>
      <motion.div variants={section}>
        <QuickActions />
      </motion.div>
      <motion.div variants={section}>
        <SafetyTip />
      </motion.div>
      <motion.div variants={section}>
        <RecentActivity />
      </motion.div>
    </motion.div>
  );
}
