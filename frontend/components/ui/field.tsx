import * as React from "react";

import { cn } from "@/lib/utils";

/** Label + control + hint/error, laid out consistently for every form. */
export function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
  className,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      <label htmlFor={htmlFor} className="block text-[13px] font-semibold text-foreground/80">
        {label}
      </label>
      {children}
      {error ? (
        <p role="alert" className="text-[13px] font-medium text-destructive">
          {error}
        </p>
      ) : hint ? (
        <div className="text-[13px] text-muted-foreground">{hint}</div>
      ) : null}
    </div>
  );
}
