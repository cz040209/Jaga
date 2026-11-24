/**
 * Form rules, mirroring the backend (backend/app/schemas/auth.py) so people
 * see mistakes instantly. The backend still checks everything again.
 */

import { z } from "zod";

/** Same rule as normalize_my_mobile(): 01x + 7-8 digits, any spacing/dashes, optional +60. */
export function isMalaysianMobile(value: string): boolean {
  let digits = value.replace(/[\s\-()]/g, "");
  if (digits.startsWith("+60")) digits = digits.slice(3);
  else if (digits.startsWith("60")) digits = digits.slice(2);
  else if (digits.startsWith("0")) digits = digits.slice(1);
  return /^1\d{8,9}$/.test(digits);
}

const email = z.email("Enter a valid email address");

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Enter your password"),
});

export const registerSchema = z.object({
  full_name: z
    .string()
    .transform((value) => value.trim().replace(/\s+/g, " "))
    .pipe(z.string().min(2, "Enter your full name").max(200, "That name is too long")),
  email,
  phone_number: z
    .string()
    .refine(isMalaysianMobile, "Enter a valid Malaysian mobile number, e.g. 012-345 6789"),
  password: z
    .string()
    .min(8, "Use at least 8 characters")
    .refine((value) => new TextEncoder().encode(value).length <= 72, "That password is too long")
    .refine((value) => value.trim() === value, "Password can't start or end with a space"),
  preferred_language: z.enum(["en", "ms", "zh"]),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;

/** A friendly 0-4 strength score for the meter. Advisory only: the rule is 8+ characters. */
export function passwordStrength(password: string): { score: 0 | 1 | 2 | 3 | 4; label: string } {
  if (!password) return { score: 0, label: "" };
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password) && /[^A-Za-z0-9]/.test(password)) score++;
  const capped = Math.min(score, 4) as 0 | 1 | 2 | 3 | 4;
  return { score: capped, label: ["Too short", "Weak", "Fair", "Good", "Strong"][capped] };
}
