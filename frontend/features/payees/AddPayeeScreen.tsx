"use client";

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, BadgeCheck, Hash, PencilLine, Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Avatar } from "@/components/shared/Avatar";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { FormAlert } from "@/features/auth/AuthCard";
import { useAddPayee, useLookupRecipient } from "@/features/payees/hooks";
import { ApiError } from "@/lib/api/errors";
import type { Recipient } from "@/types";

const DIGITS = 12; // Jaga numbers: "88" + 9 digits + 1 check digit

/** "884721930556" -> "8847 2193 0556" while typing. */
function group(digits: string) {
  return digits.replace(/(\d{4})(?=\d)/g, "$1 ");
}

export function AddPayeeScreen() {
  const router = useRouter();
  const thenTransfer = useSearchParams().get("then") === "transfer";
  const [digits, setDigits] = useState("");
  const [nickname, setNickname] = useState("");
  const [found, setFound] = useState<Recipient | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lookup = useLookupRecipient();
  const add = useAddPayee();

  function check() {
    setError(null);
    lookup.mutate(digits, {
      onSuccess: (recipient) => setFound(recipient),
      onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't check this number."),
    });
  }

  function save() {
    setError(null);
    add.mutate(
      { account_number: digits, nickname: nickname.trim() || undefined },
      {
        onSuccess: (payee) => {
          toast.success(`${payee.nickname} added`, { description: "You can send them money now." });
          router.replace(thenTransfer ? `/transfer?payee=${payee.id}` : "/payees");
        },
        onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't save. Please try again."),
      },
    );
  }

  return (
    <div>
      <PageHeader
        back="history"
        title="Add payee"
        subtitle="Enter their Jaga account number. We'll show you who it belongs to before you save."
      />

      <div className="glass space-y-5 rounded-[28px] p-5 shadow-[var(--shadow-soft)]">
        <FormAlert message={error} />

        <Field label="Account number" htmlFor="account_number" hint="12 digits, e.g. 8847 2193 0556">
          <Input
            id="account_number"
            inputMode="numeric"
            autoComplete="off"
            autoFocus
            placeholder="0000 0000 0000"
            className="[&_input]:text-[17px] [&_input]:font-semibold [&_input]:tracking-wider"
            leading={<Hash />}
            value={group(digits)}
            onChange={(event) => {
              setDigits(event.target.value.replace(/\D/g, "").slice(0, DIGITS));
              setFound(null); // a new number needs a new check
              setError(null);
            }}
          />
        </Field>

        <AnimatePresence mode="wait" initial={false}>
          {found ? (
            <motion.div
              key="found"
              initial={{ opacity: 0, y: 12, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ type: "spring", stiffness: 320, damping: 26 }}
              className="space-y-5"
            >
              <div className="flex items-center gap-3.5 rounded-3xl bg-gradient-to-br from-emerald-50 to-teal-50 p-4 ring-1 ring-emerald-100 dark:from-emerald-500/10 dark:to-teal-500/10 dark:ring-emerald-400/20">
                <Avatar name={found.masked_name} className="size-12" />
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-1.5 text-[12px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
                    <BadgeCheck className="size-4" /> Account found
                  </p>
                  <p className="truncate text-[17px] font-bold text-foreground">{found.masked_name}</p>
                  <p className="text-[13px] text-muted-foreground">{found.masked_number}</p>
                </div>
              </div>

              <div className="flex gap-3 rounded-2xl bg-amber-50 p-3.5 text-[13px] leading-relaxed text-amber-900 ring-1 ring-amber-100 dark:bg-amber-400/10 dark:text-amber-100 dark:ring-amber-400/20">
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-500" />
                <p>
                  Is this the person you expect? If someone you don&apos;t know asked you to add this account, stop.
                  Scammers often pose as police, bank or LHDN officers.
                </p>
              </div>

              <Field label="Nickname (optional)" htmlFor="nickname" hint="How they'll appear in your payee list.">
                <Input
                  id="nickname"
                  maxLength={120}
                  placeholder={found.masked_name}
                  leading={<PencilLine />}
                  value={nickname}
                  onChange={(event) => setNickname(event.target.value)}
                />
              </Field>

              <Button size="lg" className="w-full" loading={add.isPending} onClick={save}>
                {thenTransfer ? "Save and continue" : "Save payee"}
              </Button>
            </motion.div>
          ) : (
            <motion.div key="check" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Button
                size="lg"
                className="w-full"
                disabled={digits.length !== DIGITS}
                loading={lookup.isPending}
                onClick={check}
              >
                <Search /> Check account
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
