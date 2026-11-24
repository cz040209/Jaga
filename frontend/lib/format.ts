/**
 * Display helpers. Money arrives from the API as a string ("10250.50") and is
 * formatted with string operations only: never turned into a float, so no
 * rounding surprises.
 */

const MALAYSIA_TZ = "Asia/Kuala_Lumpur";

/** "10250.5" -> "10,250.50" */
export function formatAmount(amount: string): string {
  const negative = amount.startsWith("-");
  const [whole, fraction = ""] = amount.replace("-", "").split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "-" : ""}${grouped}.${fraction.padEnd(2, "0").slice(0, 2)}`;
}

/** "10250.5" -> "RM 10,250.50" */
export function formatRM(amount: string): string {
  return `RM ${formatAmount(amount)}`;
}

/** Split for big balance displays: { whole: "10,250", cents: "50" } */
export function splitAmount(amount: string): { whole: string; cents: string } {
  const [whole, cents] = formatAmount(amount).split(".");
  return { whole, cents };
}

function dayKey(date: Date): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: MALAYSIA_TZ }).format(date);
}

/** "Today, 3:58 PM" / "Yesterday, 9:02 AM" / "21 Nov, 1:15 PM" (Malaysia time) */
export function formatWhen(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const time = new Intl.DateTimeFormat("en-MY", {
    timeZone: MALAYSIA_TZ,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);

  if (dayKey(date) === dayKey(now)) return `Today, ${time}`;
  if (dayKey(date) === dayKey(yesterday)) return `Yesterday, ${time}`;
  const day = new Intl.DateTimeFormat("en-MY", {
    timeZone: MALAYSIA_TZ,
    day: "numeric",
    month: "short",
  }).format(date);
  return `${day}, ${time}`;
}

/** "Good morning" / "Good afternoon" / "Good evening", in Malaysia time */
export function greeting(): string {
  const hour = Number(
    new Intl.DateTimeFormat("en-MY", { timeZone: MALAYSIA_TZ, hour: "numeric", hour12: false })
      .format(new Date())
      .replace(/\D/g, ""),
  );
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

/** "884721930556" -> "8847 2193 0556" (only for the owner's own number) */
export function groupAccountNumber(number: string): string {
  return number.replace(/(\d{4})(?=\d)/g, "$1 ");
}

/** First name for greetings: "Aisyah Rahman" -> "Aisyah" */
export function firstName(fullName: string): string {
  return fullName.trim().split(/\s+/)[0] ?? fullName;
}

/** Day heading for grouped lists: "Today" / "Yesterday" / "Mon, 21 Nov" / "21 Nov 2025" */
export function formatDay(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  if (dayKey(date) === dayKey(now)) return "Today";
  if (dayKey(date) === dayKey(new Date(now.getTime() - 86_400_000))) return "Yesterday";
  const sameYear = dayKey(date).slice(0, 4) === dayKey(now).slice(0, 4);
  return new Intl.DateTimeFormat("en-MY", {
    timeZone: MALAYSIA_TZ,
    weekday: sameYear ? "short" : undefined,
    day: "numeric",
    month: "short",
    year: sameYear ? undefined : "numeric",
  }).format(date);
}

/** Same calendar day in Malaysia? Used to group lists under day headings. */
export function sameDay(a: string, b: string): boolean {
  return dayKey(new Date(a)) === dayKey(new Date(b));
}

/** Full date and time for receipts: "24 Nov 2026, 3:12 pm" */
export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("en-MY", {
    timeZone: MALAYSIA_TZ,
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(new Date(iso));
}

/** "just now" / "5 min ago" / "3 h ago" / "2 days ago", then a date. */
export function formatRelative(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;
  return formatDay(iso);
}

/** Initials for avatars: "Ali b** A** B**" -> "AA", "Aisyah Rahman" -> "AR" */
export function initials(name: string): string {
  const parts = name.replace(/[^\p{L}\s]/gu, " ").trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "?";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}
