import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { Customer, Device, Language, Session } from "@/types";

const keys = {
  profile: ["profile"] as const,
  sessions: ["sessions"] as const,
  devices: ["devices"] as const,
};

export function useProfile() {
  return useQuery({ queryKey: keys.profile, queryFn: () => api<Customer>("/customers/me") });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { full_name?: string; preferred_language?: Language }) =>
      api<Customer>("/customers/me", { method: "PATCH", body }),
    onSuccess: (customer) => queryClient.setQueryData(keys.profile, customer),
  });
}

export function useChangePassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      api<{ revoked_sessions: number }>("/customers/me/password", { method: "POST", body }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.sessions });
      void queryClient.invalidateQueries({ queryKey: ["inbox"] }); // "password changed" alert
    },
  });
}

export function useSessions() {
  return useQuery({ queryKey: keys.sessions, queryFn: () => api<Session[]>("/customers/me/sessions") });
}

export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/customers/me/sessions/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.sessions }),
  });
}

export function useRevokeOtherSessions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<{ revoked_sessions: number }>("/customers/me/sessions", { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.sessions }),
  });
}

export function useDevices() {
  return useQuery({ queryKey: keys.devices, queryFn: () => api<Device[]>("/customers/me/devices") });
}

export function useRenameDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      api<Device>(`/customers/me/devices/${id}`, { method: "PATCH", body: { display_name: name } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.devices }),
  });
}

export function useForgetDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/customers/me/devices/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.devices });
      void queryClient.invalidateQueries({ queryKey: keys.sessions });
    },
  });
}
