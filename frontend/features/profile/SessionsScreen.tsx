"use client";

import { AnimatePresence, motion } from "framer-motion";
import { LogOut, MapPin, MonitorSmartphone } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, LoadError } from "@/components/shared/EmptyState";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DeviceIcon, deviceName } from "@/features/profile/DevicesScreen";
import { useDevices, useRevokeOtherSessions, useRevokeSession, useSessions } from "@/features/profile/hooks";
import { formatRelative } from "@/lib/format";

export function SessionsScreen() {
  const { data: sessions, isPending, isError, refetch } = useSessions();
  const { data: devices } = useDevices();
  const revoke = useRevokeSession();
  const revokeOthers = useRevokeOtherSessions();

  // Current session first, then most recently active.
  const sorted = [...(sessions ?? [])].sort(
    (a, b) => Number(b.is_current) - Number(a.is_current) || b.last_activity_at.localeCompare(a.last_activity_at),
  );
  const others = sorted.filter((s) => !s.is_current).length;

  return (
    <div>
      <PageHeader back="/profile" title="Active sessions" subtitle="Everywhere you're signed in right now." />

      {isPending ? (
        <Skeleton className="h-[240px] w-full rounded-[28px]" />
      ) : isError ? (
        <LoadError what="your sessions" onRetry={() => refetch()} />
      ) : sorted.length === 0 ? (
        <EmptyState icon={MonitorSmartphone} title="No sessions" description="Nothing signed in." />
      ) : (
        <ul className="glass divide-y divide-border/60 rounded-[28px] px-5 shadow-[var(--shadow-soft)]">
          <AnimatePresence initial={false}>
            {sorted.map((session) => {
              const device = devices?.find((d) => d.id === session.device_id);
              const place = [session.city, session.country_code].filter(Boolean).join(", ");
              return (
                <motion.li
                  key={session.id}
                  layout
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-center gap-3.5 overflow-hidden py-4"
                >
                  <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-muted text-foreground/70">
                    <DeviceIcon os={device?.operating_system ?? null} className="size-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-[15px] font-semibold text-foreground">
                        {device ? deviceName(device) : "Unnamed device"}
                      </p>
                      {session.is_current && (
                        <span className="shrink-0 rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-bold text-teal-700 dark:bg-teal-400/15 dark:text-teal-300">
                          You&apos;re here
                        </span>
                      )}
                    </div>
                    <p className="flex items-center gap-1 truncate text-[12.5px] text-muted-foreground">
                      <MapPin className="size-3 shrink-0" />
                      {place || session.ip_address || "Unknown location"} · Active {formatRelative(session.last_activity_at)}
                    </p>
                  </div>
                  {!session.is_current && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="shrink-0 text-destructive hover:bg-destructive/10"
                      loading={revoke.isPending && revoke.variables === session.id}
                      onClick={() =>
                        revoke.mutate(session.id, {
                          onSuccess: () => toast.success("Signed out that session"),
                          onError: () => toast.error("Couldn't sign it out."),
                        })
                      }
                    >
                      Sign out
                    </Button>
                  )}
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ul>
      )}

      {others > 0 && (
        <Button
          variant="outline"
          size="lg"
          className="mt-5 w-full text-destructive hover:bg-destructive/10"
          loading={revokeOthers.isPending}
          onClick={() =>
            revokeOthers.mutate(undefined, {
              onSuccess: ({ revoked_sessions }) =>
                toast.success(`Signed out ${revoked_sessions} other session${revoked_sessions === 1 ? "" : "s"}`),
              onError: () => toast.error("Couldn't sign them out."),
            })
          }
        >
          <LogOut /> Sign out all other sessions
        </Button>
      )}
    </div>
  );
}
