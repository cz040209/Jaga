/**
 * TanStack Query hooks: caching, loading and error states for account data.
 * Components call these; they never call `api()` directly.
 */

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { getMyAccounts, getMyTransactions } from "@/features/accounts/api";

export const accountKeys = {
  all: ["accounts"] as const,
  list: () => [...accountKeys.all, "list"] as const,
  transactions: (limit: number) => [...accountKeys.all, "transactions", limit] as const,
  history: () => [...accountKeys.all, "history"] as const,
};

/** The primary account (first in the list) plus the full list. */
export function usePrimaryAccount() {
  const query = useQuery({ queryKey: accountKeys.list(), queryFn: getMyAccounts });
  return { ...query, account: query.data?.[0] };
}

/** The newest few statement lines, for the home screen. */
export function useRecentTransactions(limit = 5) {
  return useQuery({
    queryKey: accountKeys.transactions(limit),
    queryFn: () => getMyTransactions({ limit }),
  });
}

/** The full statement, 20 lines at a time ("before" = the previous page's next_cursor). */
export function useTransactionHistory() {
  return useInfiniteQuery({
    queryKey: accountKeys.history(),
    queryFn: ({ pageParam }) => getMyTransactions({ limit: 20, before: pageParam }),
    initialPageParam: undefined as number | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}
