"use client";

import { AnimatePresence, motion, useDragControls } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useId } from "react";

/**
 * Bottom sheet: slides up from the bottom, dims the page, and closes by
 * dragging it down, tapping outside, pressing Escape or the close button.
 */
export function Sheet({
  open,
  onClose,
  title,
  description,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: React.ReactNode;
  children: React.ReactNode;
}) {
  const titleId = useId();
  const drag = useDragControls();

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden"; // the page behind shouldn't scroll
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50">
          <motion.div
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="absolute inset-x-0 bottom-0 mx-auto max-h-[88dvh] max-w-md overflow-y-auto rounded-t-[32px] bg-card px-5 pb-[max(24px,env(safe-area-inset-bottom))] pt-2 shadow-[0_-20px_60px_-20px_rgb(0_0_0/0.35)]"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 38 }}
            drag="y"
            dragControls={drag}
            dragListener={false}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_, info) => {
              if (info.offset.y > 90 || info.velocity.y > 500) onClose();
            }}
          >
            {/* Grab handle: drag from here to dismiss. */}
            <div
              className="flex cursor-grab touch-none justify-center pb-3 pt-1 active:cursor-grabbing"
              onPointerDown={(event) => drag.start(event)}
            >
              <span className="h-1.5 w-10 rounded-full bg-muted-foreground/30" />
            </div>
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 id={titleId} className="text-[19px] font-bold tracking-tight text-foreground">
                  {title}
                </h2>
                {description && <p className="mt-0.5 text-[13.5px] text-muted-foreground">{description}</p>}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="grid size-9 shrink-0 place-items-center rounded-full bg-muted text-muted-foreground transition hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            </div>
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

/** One tappable row inside an action sheet. */
export function SheetAction({
  icon: Icon,
  label,
  description,
  onClick,
  tone = "default",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  description?: string;
  onClick: () => void;
  tone?: "default" | "danger";
}) {
  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className="flex w-full items-center gap-3.5 rounded-2xl px-2 py-3 text-left transition-colors hover:bg-muted"
    >
      <span
        className={
          tone === "danger"
            ? "grid size-11 place-items-center rounded-2xl bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300"
            : "grid size-11 place-items-center rounded-2xl bg-muted text-foreground/80"
        }
      >
        <Icon className="size-5" />
      </span>
      <span className="min-w-0">
        <span
          className={`block text-[15px] font-semibold ${tone === "danger" ? "text-rose-600 dark:text-rose-300" : "text-foreground"}`}
        >
          {label}
        </span>
        {description && <span className="block text-[12.5px] text-muted-foreground">{description}</span>}
      </span>
    </motion.button>
  );
}
