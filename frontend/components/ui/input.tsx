import * as React from "react";

import { cn } from "@/lib/utils";

type InputProps = React.ComponentProps<"input"> & {
  /** Icon shown inside the field on the left. */
  leading?: React.ReactNode;
  /** Element shown inside the field on the right (e.g. a show-password button). */
  trailing?: React.ReactNode;
  invalid?: boolean;
};

export function Input({ className, leading, trailing, invalid, ...props }: InputProps) {
  return (
    <div
      className={cn(
        "group flex h-14 w-full items-center gap-3 rounded-2xl border bg-white/80 px-4 dark:bg-slate-900/60 shadow-[0_1px_2px_rgb(15_23_42/0.04)] backdrop-blur transition-all duration-200",
        "border-slate-200/80 hover:border-slate-300 focus-within:border-teal-400 focus-within:bg-white dark:border-white/10 dark:hover:border-white/20 dark:focus-within:border-teal-400/70 dark:focus-within:bg-slate-900 focus-within:shadow-[0_0_0_4px_rgb(20_184_166/0.12)]",
        invalid &&
          "border-rose-300 focus-within:border-rose-400 focus-within:shadow-[0_0_0_4px_rgb(225_29_72/0.10)]",
        className,
      )}
    >
      {leading && (
        <span className="text-slate-400 transition-colors group-focus-within:text-teal-600 dark:text-slate-500 dark:group-focus-within:text-teal-400 [&_svg]:size-5">
          {leading}
        </span>
      )}
      <input
        className="h-full w-full min-w-0 bg-transparent text-[15px] text-foreground outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500"
        aria-invalid={invalid || undefined}
        {...props}
      />
      {trailing}
    </div>
  );
}
