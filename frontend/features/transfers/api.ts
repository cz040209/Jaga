import { api } from "@/lib/api/client";
import type { Transfer } from "@/types";

export type SendTransferBody = { payee_id: number; amount: string; note?: string };

/**
 * The Idempotency-Key makes "Send" safe to retry: if the network drops after
 * the bank moved the money, sending again with the SAME key returns the
 * original transfer instead of paying twice.
 */
export const sendTransfer = (body: SendTransferBody, idempotencyKey: string) =>
  api<Transfer>("/transfers", { method: "POST", body, headers: { "Idempotency-Key": idempotencyKey } });

export const getTransfer = (id: number) => api<Transfer>(`/transfers/${id}`);
