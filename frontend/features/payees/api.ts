import { api } from "@/lib/api/client";
import type { Payee, Recipient } from "@/types";

export const listPayees = () => api<Payee[]>("/payees");

export const lookupRecipient = (accountNumber: string) =>
  api<Recipient>(`/payees/lookup?account_number=${encodeURIComponent(accountNumber)}`);

export const addPayee = (body: { account_number: string; nickname?: string }) =>
  api<Payee>("/payees", { method: "POST", body });

export const renamePayee = (id: number, nickname: string) =>
  api<Payee>(`/payees/${id}`, { method: "PATCH", body: { nickname } });

export const removePayee = (id: number) => api<void>(`/payees/${id}`, { method: "DELETE" });
