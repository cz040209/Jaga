/**
 * Button styles, in a plain (non-client) module so server components can
 * style links as buttons too: <Link className={buttonVariants()} />.
 */

import { cva } from "class-variance-authority";

/** shadcn/ui-style variants, restyled for Jaga: pill shapes, teal gradient, soft glow. */
export const buttonVariants = cva(
  "relative inline-flex select-none items-center justify-center gap-2 overflow-hidden whitespace-nowrap rounded-full text-sm font-semibold transition-[background,box-shadow,color] duration-200 outline-none focus-visible:ring-4 focus-visible:ring-ring/25 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-[18px] [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-to-b from-teal-500 to-teal-600 text-white shadow-[var(--shadow-glow)] hover:from-teal-500 hover:to-teal-700",
        secondary: "bg-secondary text-secondary-foreground hover:bg-teal-100 dark:hover:bg-teal-400/20",
        outline: "glass text-foreground shadow-[var(--shadow-soft)] hover:bg-white dark:hover:bg-slate-800/80",
        ghost: "text-foreground hover:bg-slate-900/5 dark:hover:bg-white/10",
        link: "text-primary underline-offset-4 hover:underline",
        destructive: "bg-rose-600 text-white hover:bg-rose-700",
      },
      size: {
        lg: "h-14 px-7 text-[15px]",
        md: "h-12 px-6",
        sm: "h-9 px-4 text-[13px]",
        icon: "size-11",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);
