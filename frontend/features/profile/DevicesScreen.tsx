"use client";

import { motion } from "framer-motion";
import { Laptop, Monitor, PencilLine, ShieldCheck, ShieldX, Smartphone, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState, LoadError } from "@/components/shared/EmptyState";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetAction } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useDevices, useForgetDevice, useRenameDevice } from "@/features/profile/hooks";
import { formatRelative } from "@/lib/format";
import type { Device } from "@/types";

export function deviceName(device: Pick<Device, "display_name" | "browser" | "operating_system">) {
  if (device.display_name) return device.display_name;
  if (device.browser && device.operating_system) return `${device.browser} on ${device.operating_system}`;
  return device.browser ?? device.operating_system ?? "Unnamed device"; // until the backend parses User-Agents
}

export function DeviceIcon({ os, className }: { os: string | null; className?: string }) {
  const name = (os ?? "").toLowerCase();
  const Icon = /ios|iphone|ipad|android/.test(name) ? Smartphone : /mac|windows|linux|chrome os/.test(name) ? Laptop : Monitor;
  return <Icon className={className} />;
}

function Trust({ status }: { status: Device["trust_status"] }) {
  if (status === "trusted")
    return (
      <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-emerald-600 dark:text-emerald-400">
        <ShieldCheck className="size-3.5" /> Trusted
      </span>
    );
  if (status === "blocked")
    return (
      <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-rose-600 dark:text-rose-300">
        <ShieldX className="size-3.5" /> Blocked
      </span>
    );
  return <span className="text-[12px] font-semibold text-muted-foreground">Not yet trusted</span>;
}

function RenameDevice({ device, onDone }: { device: Device; onDone: () => void }) {
  const [name, setName] = useState(device.display_name ?? "");
  const rename = useRenameDevice();
  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!name.trim()) return;
        rename.mutate(
          { id: device.id, name: name.trim() },
          { onSuccess: () => (toast.success("Device renamed"), onDone()), onError: () => toast.error("Couldn't rename.") },
        );
      }}
    >
      <Input autoFocus value={name} maxLength={120} placeholder={deviceName(device)} onChange={(e) => setName(e.target.value)} aria-label="Device name" leading={<PencilLine />} />
      <Button type="submit" size="lg" className="w-full" loading={rename.isPending} disabled={!name.trim()}>
        Save name
      </Button>
    </form>
  );
}

export function DevicesScreen() {
  const { data: devices, isPending, isError, refetch } = useDevices();
  const forget = useForgetDevice();
  const [selected, setSelected] = useState<Device | null>(null);
  const [open, setOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);

  return (
    <div>
      <PageHeader back="/profile" title="Devices" subtitle="Phones and computers that have signed in to your account." />

      {isPending ? (
        <Skeleton className="h-[220px] w-full rounded-[28px]" />
      ) : isError ? (
        <LoadError what="your devices" onRetry={() => refetch()} />
      ) : devices.length === 0 ? (
        <EmptyState icon={Laptop} title="No devices" description="Devices you sign in with will show up here." />
      ) : (
        <motion.ul
          className="glass divide-y divide-border/60 rounded-[28px] px-5 shadow-[var(--shadow-soft)]"
          initial="hidden"
          animate="show"
          variants={{ show: { transition: { staggerChildren: 0.05 } } }}
        >
          {devices.map((device) => (
            <motion.li key={device.id} variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}>
              <button
                type="button"
                onClick={() => {
                  setSelected(device);
                  setRenaming(false);
                  setOpen(true);
                }}
                className="flex w-full items-center gap-3.5 py-4 text-left"
              >
                <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-muted text-foreground/70">
                  <DeviceIcon os={device.operating_system} className="size-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-[15px] font-semibold text-foreground">{deviceName(device)}</p>
                    {device.is_current && (
                      <span className="shrink-0 rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-bold text-teal-700 dark:bg-teal-400/15 dark:text-teal-300">
                        This device
                      </span>
                    )}
                  </div>
                  <p className="text-[12.5px] text-muted-foreground">
                    <Trust status={device.trust_status} /> · Active {formatRelative(device.last_seen_at)}
                  </p>
                </div>
              </button>
            </motion.li>
          ))}
        </motion.ul>
      )}

      <p className="mt-4 px-1 text-[12.5px] leading-relaxed text-muted-foreground">
        Don&apos;t recognise a device? Remove it, then change your password.
      </p>

      <Sheet
        open={open}
        onClose={() => setOpen(false)}
        title={renaming ? "Rename device" : selected ? deviceName(selected) : ""}
        description={!renaming && selected ? `First seen ${formatRelative(selected.first_seen_at)}` : undefined}
      >
        {selected && renaming && <RenameDevice device={selected} onDone={() => setOpen(false)} />}
        {selected && !renaming && (
          <div className="space-y-1">
            <SheetAction icon={PencilLine} label="Rename" description="e.g. “My iPhone”" onClick={() => setRenaming(true)} />
            {!selected.is_current && (
              <SheetAction
                icon={Trash2}
                tone="danger"
                label="Remove device"
                description="It will need to be recognised again next time"
                onClick={() =>
                  forget.mutate(selected.id, {
                    onSuccess: () => {
                      toast.success("Device removed");
                      setOpen(false);
                    },
                    onError: () => toast.error("Couldn't remove it."),
                  })
                }
              />
            )}
          </div>
        )}
      </Sheet>
    </div>
  );
}
