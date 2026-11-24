"use client";

import { motion } from "framer-motion";
import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/components/theme/ThemeProvider";
import { cn } from "@/lib/utils";

/**
 * Round glass button that flips between light and dark.
 * Both icons are always rendered and CSS picks one from the `.dark` class,
 * so the right icon shows from the very first paint (no flicker on reload).
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.9 }}
      transition={{ type: "spring", stiffness: 500, damping: 26 }}
      onClick={(event) => {
        const box = event.currentTarget.getBoundingClientRect();
        setTheme(resolvedTheme === "dark" ? "light" : "dark", {
          x: box.left + box.width / 2,
          y: box.top + box.height / 2,
        });
      }}
      aria-label="Switch between light and dark theme"
      className={cn(
        "glass relative grid size-12 place-items-center overflow-hidden rounded-full text-foreground/70 shadow-[var(--shadow-soft)] transition-colors hover:text-foreground",
        className,
      )}
    >
      <Sun
        className="absolute size-5 text-amber-500 transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] dark:rotate-90 dark:scale-0 dark:opacity-0"
        aria-hidden
      />
      <Moon
        className="absolute size-5 -rotate-90 scale-0 text-sky-300 opacity-0 transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] dark:rotate-0 dark:scale-100 dark:opacity-100"
        aria-hidden
      />
    </motion.button>
  );
}
