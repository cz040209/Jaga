import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { accountKeys } from "@/features/accounts/hooks";
import { getTransfer, sendTransfer, type SendTransferBody } from "@/features/transfers/api";

export function useSendTransfer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ body, key }: { body: SendTransferBody; key: string }) => sendTransfer(body, key),
    onSuccess: (transfer) => {
      queryClient.setQueryData(["transfer", transfer.id], transfer);
      // Balance, history and the inbox badge all changed.
      void queryClient.invalidateQueries({ queryKey: accountKeys.all });
      void queryClient.invalidateQueries({ queryKey: ["inbox"] });
    },
  });
}

export function useTransfer(id: number) {
  return useQuery({ queryKey: ["transfer", id], queryFn: () => getTransfer(id), enabled: id > 0 });
}
