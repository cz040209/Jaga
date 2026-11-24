/**
 * Money as text, never floats: "250.5" is compared and validated in whole sen
 * (cents) using BigInt, so RM 0.10 + RM 0.20 is always exactly RM 0.30.
 */

export function toSen(amount: string): bigint {
  const [whole = "0", fraction = ""] = amount.split(".");
  return BigInt(whole || "0") * BigInt(100) + BigInt((fraction + "00").slice(0, 2));
}

/** "250.5" -> "250.50" (what the API receives) */
export function normalise(amount: string): string {
  const [whole = "0", fraction = ""] = amount.split(".");
  return `${BigInt(whole || "0").toString()}.${(fraction + "00").slice(0, 2)}`;
}

const MAX_WHOLE_DIGITS = 7; // up to RM 9,999,999.99

/** Apply one keypad press to the amount being typed. */
export function pressKey(amount: string, key: string): string {
  if (key === "back") return amount.slice(0, -1);
  if (key === ".") {
    if (amount.includes(".")) return amount;
    return (amount || "0") + ".";
  }
  if (!/^\d$/.test(key)) return amount;
  const [whole, fraction] = amount.split(".");
  if (fraction !== undefined) return fraction.length >= 2 ? amount : amount + key;
  if (whole === "0") return key; // no leading zeros
  if (whole.length >= MAX_WHOLE_DIGITS) return amount;
  return amount + key;
}
