"use client";

import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const backClass =
  "glass grid size-11 shrink-0 place-items-center rounded-full text-foreground/70 shadow-[var(--shadow-soft)] transition hover:text-foreground";

/**
 * Screen title row. Tab screens show just a big title; sub-screens get a back
 * button (to `back`, or the previous page when `back` is "history").
 */
export function PageHeader({
  title,
  subtitle,
  back,
  action,
}: {
  title: string;
  subtitle?: React.ReactNode;
  back?: string | "history";
  action?: React.ReactNode;
}) {
  const router = useRouter();

  return (
    <header className="mb-5">
      {back && (
        <div className="mb-4 flex items-center justify-between">
          {back === "history" ? (
            <motion.button
              type="button"
              whileTap={{ scale: 0.9 }}
              onClick={() => router.back()}
              aria-label="Back"
              className={backClass}
            >
              <ArrowLeft className="size-5" />
            </motion.button>
          ) : (
            <Link href={back} aria-label="Back" className={backClass}>
              <ArrowLeft className="size-5" />
            </Link>
          )}
        </div>
      )}
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-[28px] font-extrabold leading-tight tracking-tight text-foreground">{title}</h1>
          {subtitle && <p className="mt-1 text-[14px] text-muted-foreground">{subtitle}</p>}
        </div>
        {action}
      </div>
    </header>
  );
}
