"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, Bell, Home, User, Users } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useUnreadCount } from "@/features/inbox/hooks";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/home", label: "Home", icon: Home },
  { href: "/payees", label: "Payees", icon: Users },
  { href: "/inbox", label: "Inbox", icon: Bell },
  { href: "/profile", label: "Profile", icon: User },
] as const;

function Tab({ href, label, icon: Icon, badge }: (typeof TABS)[number] & { badge?: number }) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative flex h-14 flex-1 flex-col items-center justify-center gap-0.5 rounded-2xl text-[11px] font-semibold transition-colors",
        active ? "text-teal-700 dark:text-teal-300" : "text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300",
      )}
    >
      {/* The highlight pill: one shared element that slides to the active tab. */}
      {active && (
        <motion.span
          layoutId="nav-pill"
          className="absolute inset-x-1 inset-y-1 -z-10 rounded-2xl bg-teal-50 dark:bg-teal-400/15"
          transition={{ type: "spring", stiffness: 420, damping: 34 }}
        />
      )}
      <motion.span
        className="relative"
        animate={{ y: active ? -1 : 0, scale: active ? 1.08 : 1 }}
        transition={{ type: "spring", stiffness: 500, damping: 28 }}
      >
        <Icon className="size-[22px]" strokeWidth={active ? 2.4 : 2} />
        <AnimatePresence>
          {badge ? (
            <motion.span
              key="badge"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              transition={{ type: "spring", stiffness: 500, damping: 20 }}
              className="absolute -right-2.5 -top-1.5 grid h-[18px] min-w-[18px] place-items-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white ring-2 ring-white dark:ring-slate-900"
            >
              {badge > 99 ? "99+" : badge}
            </motion.span>
          ) : null}
        </AnimatePresence>
      </motion.span>
      {label}
    </Link>
  );
}

const MotionLink = motion.create(Link);

export function BottomNav() {
  const unread = useUnreadCount();
  return (
    <nav
      aria-label="Main"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-40 mx-auto max-w-md px-4 pb-[max(14px,env(safe-area-inset-bottom))]"
    >
      <motion.div
        initial={{ y: 80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 260, damping: 28, delay: 0.1 }}
        className="glass pointer-events-auto relative isolate flex items-center gap-1 rounded-[28px] p-1.5 shadow-[var(--shadow-float)]"
      >
        <Tab {...TABS[0]} />
        <Tab {...TABS[1]} />
        {/* Centre action: the thing people open a bank app to do. */}
        <div className="flex flex-1 justify-center">
          <MotionLink
            href="/transfer"
            aria-label="Transfer money"
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.9 }}
            transition={{ type: "spring", stiffness: 400, damping: 20 }}
            className="-mt-9 grid size-[60px] place-items-center rounded-[22px] bg-gradient-to-br from-teal-400 to-teal-600 text-white shadow-[var(--shadow-glow)] ring-[6px] ring-background"
          >
            <ArrowUpRight className="size-7" strokeWidth={2.4} />
          </MotionLink>
        </div>
        <Tab {...TABS[2]} badge={unread} />
        <Tab {...TABS[3]} />
      </motion.div>
    </nav>
  );
}
