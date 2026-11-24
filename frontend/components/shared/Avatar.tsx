import { initials } from "@/lib/format";
import { cn } from "@/lib/utils";

const GRADIENTS = [
  "from-teal-400 to-teal-600",
  "from-sky-400 to-blue-500",
  "from-violet-400 to-indigo-500",
  "from-amber-300 to-orange-500",
  "from-rose-400 to-pink-500",
  "from-emerald-400 to-green-600",
];

/** Initials on a gradient. The same name always gets the same colour. */
export function Avatar({ name, className }: { name: string; className?: string }) {
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return (
    <span
      aria-hidden
      className={cn(
        "grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br text-[14px] font-bold text-white shadow-sm",
        GRADIENTS[hash % GRADIENTS.length],
        className,
      )}
    >
      {initials(name)}
    </span>
  );
}
