"use client";

import { passwordStrength } from "@/features/auth/schemas";
import { cn } from "@/lib/utils";

/** Four bars that fill and change colour as the password gets stronger. */
export function StrengthMeter({ password }: { password: string }) {
  const { score, label } = passwordStrength(password);
  if (!password) return <>At least 8 characters. A short sentence works well.</>;
  const colours = ["bg-rose-500", "bg-rose-500", "bg-amber-500", "bg-teal-500", "bg-emerald-500"];
  return (
    <div className="flex items-center gap-3">
      <div className="flex flex-1 gap-1.5" aria-hidden>
        {[1, 2, 3, 4].map((step) => (
          <span
            key={step}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-colors duration-300",
              step <= score ? colours[score] : "bg-muted",
            )}
          />
        ))}
      </div>
      <span className="w-16 text-right font-semibold text-foreground/70">{label}</span>
    </div>
  );
}
