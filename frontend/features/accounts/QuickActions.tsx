"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, History, ShieldCheck, Users } from "lucide-react";
import Link from "next/link";

const ACTIONS = [
  { href: "/transfer", label: "Transfer", icon: ArrowUpRight, chip: "from-teal-400 to-teal-600 shadow-teal-500/40" },
  { href: "/payees", label: "Payees", icon: Users, chip: "from-sky-400 to-blue-500 shadow-sky-500/40" },
  { href: "/history", label: "History", icon: History, chip: "from-violet-400 to-indigo-500 shadow-violet-500/40" },
  { href: "/profile", label: "Security", icon: ShieldCheck, chip: "from-amber-300 to-orange-500 shadow-amber-500/40" },
] as const;

const MotionLink = motion.create(Link);

export function QuickActions() {
  return (
    <nav aria-label="Quick actions" className="glass grid grid-cols-4 rounded-[28px] p-2 shadow-[var(--shadow-soft)]">
      {ACTIONS.map(({ href, label, icon: Icon, chip }) => (
        <MotionLink
          key={href}
          href={href}
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.92 }}
          transition={{ type: "spring", stiffness: 400, damping: 22 }}
          className="flex flex-col items-center gap-2 rounded-3xl py-3 outline-none focus-visible:ring-4 focus-visible:ring-ring/25"
        >
          <span
            className={`grid size-12 place-items-center rounded-2xl bg-gradient-to-br text-white shadow-lg ${chip}`}
          >
            <Icon className="size-[22px]" strokeWidth={2.2} />
          </span>
          <span className="text-[12.5px] font-semibold text-foreground/70">{label}</span>
        </MotionLink>
      ))}
    </nav>
  );
}
