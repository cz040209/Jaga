import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { addPayee, listPayees, lookupRecipient, removePayee, renamePayee } from "@/features/payees/api";

export const payeeKeys = { all: ["payees"] as const };

export function usePayees() {
  return useQuery({ queryKey: payeeKeys.all, queryFn: listPayees });
}

export function useLookupRecipient() {
  return useMutation({ mutationFn: lookupRecipient });
}

export function useAddPayee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: addPayee,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: payeeKeys.all }),
  });
}

export function useRenamePayee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, nickname }: { id: number; nickname: string }) => renamePayee(id, nickname),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: payeeKeys.all }),
  });
}

export function useRemovePayee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: removePayee,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: payeeKeys.all }),
  });
}
