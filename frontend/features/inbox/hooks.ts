import { useInfiniteQuery, useMutation, useQuery, useQueryClient, type InfiniteData } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { Inbox } from "@/types";

const inboxKeys = {
  all: ["inbox"] as const,
  unread: ["inbox", "unread"] as const,
  list: ["inbox", "list"] as const,
};

/**
 * Unread count for the bell badge. Asks for one message only (the count comes
 * with it) and re-checks every 20 seconds and whenever the app regains focus.
 */
export function useUnreadCount() {
  const query = useQuery({
    queryKey: inboxKeys.unread,
    queryFn: () => api<Inbox>("/inbox?limit=1"),
    refetchInterval: 20_000,
  });
  return query.data?.unread_count ?? 0;
}

/** All messages, newest first, 20 at a time. */
export function useInbox() {
  return useInfiniteQuery({
    queryKey: inboxKeys.list,
    queryFn: ({ pageParam }) => api<Inbox>(`/inbox?limit=20${pageParam ? `&before=${pageParam}` : ""}`),
    initialPageParam: undefined as number | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

/** Mark one message read. The screen updates instantly; the server catches up. */
export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/inbox/${id}/read`, { method: "POST" }),
    onMutate: (id) => {
      queryClient.setQueryData<InfiniteData<Inbox>>(inboxKeys.list, (data) =>
        data && {
          ...data,
          pages: data.pages.map((page) => ({
            ...page,
            items: page.items.map((m) => (m.id === id ? { ...m, read: true } : m)),
          })),
        },
      );
      queryClient.setQueryData<Inbox>(inboxKeys.unread, (data) =>
        data && { ...data, unread_count: Math.max(0, data.unread_count - 1) },
      );
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: inboxKeys.all }),
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<{ marked: number }>("/inbox/read-all", { method: "POST" }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: inboxKeys.all }),
  });
}
