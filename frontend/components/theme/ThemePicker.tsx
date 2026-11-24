"use client";

import { motion } from "framer-motion";
import { Monitor, Moon, Sun } from "lucide-react";

import { useTheme, type Theme } from "@/components/theme/ThemeProvider";
import { cn } from "@/lib/utils";

const OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

/** Light / Dark / System segmented control with a sliding pill (used on Profile). */
export function ThemePicker() {
  const { theme, setTheme } = useTheme();

  return (
    <div role="radiogroup" aria-label="Theme" className="grid grid-cols-3 gap-1 rounded-2xl bg-muted p-1">
      {OPTIONS.map(({ value, label, icon: Icon }) => {
        const selected = theme === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={(event) => {
              const box = event.currentTarget.getBoundingClientRect();
              setTheme(value, { x: box.left + box.width / 2, y: box.top + box.height / 2 });
            }}
            className={cn(
              "relative flex h-11 items-center justify-center gap-1.5 rounded-xl text-[14px] font-semibold transition-colors",
              selected ? "text-teal-700 dark:text-teal-300" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {selected && (
              <motion.span
                layoutId="theme-pill"
                className="absolute inset-0 rounded-xl bg-card shadow-sm"
                transition={{ type: "spring", stiffness: 450, damping: 34 }}
              />
            )}
            <Icon className="relative size-4" />
            <span className="relative">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
