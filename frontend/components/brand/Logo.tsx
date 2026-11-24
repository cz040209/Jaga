import { cn } from "@/lib/utils";

/**
 * Jaga's mark: a two-tone shield holding a "J" ("jaga" = guard),
 * on a glossy teal app-icon tile. Same file as app/icon.svg (the browser tab icon).
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={cn("size-10", className)} aria-hidden>
      <defs>
        <linearGradient id="jaga-tile" x1="4" y1="2" x2="44" y2="46" gradientUnits="userSpaceOnUse">
          <stop stopColor="#5eead4" />
          <stop offset="0.45" stopColor="#14b8a6" />
          <stop offset="1" stopColor="#0e7490" />
        </linearGradient>
        <radialGradient id="jaga-gloss" cx="14" cy="8" r="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="#fff" stopOpacity="0.45" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Tile: gradient, soft gloss from the top-left, hairline inner edge. */}
      <rect x="2" y="2" width="44" height="44" rx="14" fill="url(#jaga-tile)" />
      <rect x="2" y="2" width="44" height="44" rx="14" fill="url(#jaga-gloss)" />
      <rect x="2.5" y="2.5" width="43" height="43" rx="13.5" stroke="#fff" strokeOpacity="0.25" />

      {/* Shield: white, with a mint right half so it reads as 3D. */}
      <path
        d="M24 9.5 12.5 13.8v8.4c0 7.3 4.8 13.6 11.5 16.1 6.7-2.5 11.5-8.8 11.5-16.1v-8.4L24 9.5Z"
        fill="#fff"
      />
      <path d="M24 9.5v28.8c6.7-2.5 11.5-8.8 11.5-16.1v-8.4L24 9.5Z" fill="#99f6e4" fillOpacity="0.55" />

      {/* The J. */}
      <path
        d="M27.2 17.5v7.2a4.4 4.4 0 0 1-7.8 2.8"
        stroke="#0f766e"
        strokeWidth="3.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Mark + lowercase wordmark. */
export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark className="size-10 drop-shadow-[0_6px_14px_rgb(13_148_136/0.3)]" />
      <span className="text-[26px] font-extrabold leading-none tracking-[-0.045em] text-foreground">
        jaga
      </span>
    </span>
  );
}
