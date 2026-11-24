"use client";

import { motion } from "framer-motion";
import { Delete } from "lucide-react";

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "0", "back"] as const;

/** Phone-style number pad for typing an amount. */
export function Keypad({ onKey }: { onKey: (key: string) => void }) {
  return (
    <div className="grid grid-cols-3 gap-2" role="group" aria-label="Number pad">
      {KEYS.map((key) => (
        <motion.button
          key={key}
          type="button"
          whileTap={{ scale: 0.88, backgroundColor: "rgb(20 184 166 / 0.14)" }}
          transition={{ type: "spring", stiffness: 600, damping: 30 }}
          onClick={() => {
            navigator.vibrate?.(8);
            onKey(key);
          }}
          aria-label={key === "back" ? "Delete" : key === "." ? "Decimal point" : key}
          className="grid h-14 place-items-center rounded-2xl text-[24px] font-semibold text-foreground transition-colors hover:bg-muted"
        >
          {key === "back" ? <Delete className="size-6" /> : key}
        </motion.button>
      ))}
    </div>
  );
}
