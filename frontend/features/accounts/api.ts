/** One function per backend endpoint (like the backend's crud/ layer). */

import { api } from "@/lib/api/client";
import type { Account, TransactionPage } from "@/types";

export function getMyAccounts(): Promise<Account[]> {
  return api<Account[]>("/accounts/me");
}

export function getMyTransactions(params: { limit: number; before?: number }) {
  const query = new URLSearchParams({ limit: String(params.limit) });
  if (params.before) query.set("before", String(params.before));
  return api<TransactionPage>(`/accounts/me/transactions?${query}`);
}
