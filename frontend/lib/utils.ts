import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Join class names and let later Tailwind classes win ("p-2" + "p-4" -> "p-4"). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
