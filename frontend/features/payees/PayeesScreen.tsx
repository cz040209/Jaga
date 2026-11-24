"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, PencilLine, Plus, Search, Trash2, UsersRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Avatar } from "@/components/shared/Avatar";
import { EmptyState, LoadError } from "@/components/shared/EmptyState";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button-variants";
import { Input } from "@/components/ui/input";
import { Sheet, SheetAction } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { usePayees, useRemovePayee, useRenamePayee } from "@/features/payees/hooks";
import { PayeeRow } from "@/features/payees/PayeeRow";
import { ApiError } from "@/lib/api/errors";
import type { Payee } from "@/types";

type Mode = "actions" | "rename" | "remove";

function RenameForm({ payee, onDone }: { payee: Payee; onDone: () => void }) {
  const [nickname, setNickname] = useState(payee.nickname);
  const rename = useRenamePayee();
  const trimmed = nickname.trim();

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!trimmed || trimmed === payee.nickname) return onDone();
        rename.mutate(
          { id: payee.id, nickname: trimmed },
          {
            onSuccess: () => {
              toast.success("Payee renamed");
              onDone();
            },
            onError: (error) => toast.error(error instanceof ApiError ? error.message : "Couldn't rename."),
          },
        );
      }}
    >
      <Input
        autoFocus
        value={nickname}
        maxLength={120}
        onChange={(event) => setNickname(event.target.value)}
        aria-label="Nickname"
        leading={<PencilLine />}
      />
      <Button type="submit" size="lg" className="w-full" loading={rename.isPending} disabled={!trimmed}>
        Save name
      </Button>
    </form>
  );
}

function RemoveConfirm({ payee, onDone }: { payee: Payee; onDone: () => void }) {
  const remove = useRemovePayee();
  return (
    <div className="space-y-3">
      <p className="text-[14px] leading-relaxed text-muted-foreground">
        Your past transfers to {payee.nickname} stay in your history. You can add them again anytime.
      </p>
      <Button
        variant="destructive"
        size="lg"
        className="w-full"
        loading={remove.isPending}
        onClick={() =>
          remove.mutate(payee.id, {
            onSuccess: () => {
              toast.success(`${payee.nickname} removed`);
              onDone();
            },
            onError: () => toast.error("Couldn't remove. Please try again."),
          })
        }
      >
        <Trash2 /> Remove payee
      </Button>
      <Button variant="ghost" size="lg" className="w-full" onClick={onDone}>
        Keep
      </Button>
    </div>
  );
}

export function PayeesScreen() {
  const router = useRouter();
  const { data: payees, isPending, isError, refetch } = usePayees();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Payee | null>(null);
  const [mode, setMode] = useState<Mode>("actions");
  const [sheetOpen, setSheetOpen] = useState(false); // selected stays set while the sheet slides away

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!payees || !q) return payees ?? [];
    return payees.filter(
      (payee) =>
        payee.nickname.toLowerCase().includes(q) ||
        payee.recipient.masked_name.toLowerCase().includes(q) ||
        payee.recipient.masked_number.includes(q),
    );
  }, [payees, query]);

  const close = () => setSheetOpen(false);
  const open = (payee: Payee) => {
    setMode("actions");
    setSelected(payee);
    setSheetOpen(true);
  };

  return (
    <div>
      <PageHeader
        title="Payees"
        subtitle="People you send money to."
        action={
          <Link href="/payees/new" className={buttonVariants({ size: "sm", className: "h-10 px-4" })}>
            <Plus /> Add
          </Link>
        }
      />

      {isPending ? (
        <div className="glass space-y-4 rounded-[28px] p-5 shadow-[var(--shadow-soft)]">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-3.5">
              <Skeleton className="size-11 rounded-2xl" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-3 w-2/3" />
              </div>
            </div>
          ))}
        </div>
      ) : isError ? (
        <LoadError what="your payees" onRetry={() => refetch()} />
      ) : payees.length === 0 ? (
        <div className="glass rounded-[28px] shadow-[var(--shadow-soft)]">
          <EmptyState
            icon={UsersRound}
            title="No payees yet"
            description="Add someone's Jaga account number. We'll show you their name first, so you know it's the right person."
            action={
              <Link href="/payees/new" className={buttonVariants()}>
                <Plus /> Add your first payee
              </Link>
            }
          />
        </div>
      ) : (
        <>
          {payees.length > 4 && (
            <Input
              className="mb-4"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search payees"
              aria-label="Search payees"
              leading={<Search />}
            />
          )}

          {/* Quick-send strip: the first few payees as round avatars. */}
          {payees.length >= 3 && (
            <div className="-mx-5 mb-4 flex gap-4 overflow-x-auto px-5 pb-1 [scrollbar-width:none]">
              {payees.slice(0, 8).map((payee, index) => (
                <motion.div
                  key={payee.id}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ type: "spring", stiffness: 400, damping: 24, delay: index * 0.04 }}
                >
                  <Link
                    href={`/transfer?payee=${payee.id}`}
                    className="flex w-16 flex-col items-center gap-1.5 text-center"
                  >
                    <Avatar name={payee.nickname} className="size-14 rounded-full text-[16px] shadow-md" />
                    <span className="w-full truncate text-[12px] font-semibold text-foreground/80">
                      {payee.nickname.split(" ")[0]}
                    </span>
                  </Link>
                </motion.div>
              ))}
            </div>
          )}

          <motion.ul
            className="glass rounded-[28px] px-5 py-2 shadow-[var(--shadow-soft)]"
            initial="hidden"
            animate="show"
            variants={{ show: { transition: { staggerChildren: 0.05 } } }}
          >
            {filtered.map((payee) => (
              <motion.li
                key={payee.id}
                variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}
              >
                <PayeeRow payee={payee} onClick={() => open(payee)} />
              </motion.li>
            ))}
            {filtered.length === 0 && (
              <li className="py-8 text-center text-[14px] text-muted-foreground">
                No payee matches &ldquo;{query}&rdquo;.
              </li>
            )}
          </motion.ul>
        </>
      )}

      <Sheet
        open={sheetOpen}
        onClose={close}
        title={
          mode === "rename" ? "Rename payee" : mode === "remove" ? `Remove ${selected?.nickname}?` : (selected?.nickname ?? "")
        }
        description={
          mode === "actions" && selected
            ? `${selected.recipient.masked_name} · ${selected.recipient.masked_number}`
            : undefined
        }
      >
        {selected && mode === "actions" && (
          <div className="space-y-1">
            <SheetAction
              icon={ArrowUpRight}
              label="Send money"
              description="Transfer to this payee"
              onClick={() => router.push(`/transfer?payee=${selected.id}`)}
            />
            <SheetAction icon={PencilLine} label="Rename" description="Change how they appear to you" onClick={() => setMode("rename")} />
            <SheetAction icon={Trash2} label="Remove" tone="danger" onClick={() => setMode("remove")} />
          </div>
        )}
        {selected && mode === "rename" && <RenameForm payee={selected} onDone={close} />}
        {selected && mode === "remove" && <RemoveConfirm payee={selected} onDone={close} />}
      </Sheet>
    </div>
  );
}
