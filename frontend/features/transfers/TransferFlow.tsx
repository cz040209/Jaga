"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Clock, MessageSquareText, Plus, Search, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Avatar } from "@/components/shared/Avatar";
import { EmptyState, LoadError } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { usePrimaryAccount } from "@/features/accounts/hooks";
import { FormAlert } from "@/features/auth/AuthCard";
import { usePayees } from "@/features/payees/hooks";
import { PayeeRow } from "@/features/payees/PayeeRow";
import { HoldToSend } from "@/features/transfers/HoldToSend";
import { useSendTransfer } from "@/features/transfers/hooks";
import { Keypad } from "@/features/transfers/Keypad";
import { normalise, pressKey, toSen } from "@/features/transfers/money";
import { TransferSuccess } from "@/features/transfers/TransferSuccess";
import { ApiError } from "@/lib/api/errors";
import { formatAmount, formatRM } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Payee } from "@/types";

type Step = "payee" | "amount" | "review";
const STEPS: Step[] = ["payee", "amount", "review"];
const TITLES: Record<Step, string> = { payee: "Send to", amount: "How much?", review: "Review" };
const QUICK = ["50", "100", "200", "500"];

/** Slide direction follows the step order: forward slides left, back slides right. */
const slide = {
  enter: (dir: number) => ({ x: dir * 48, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: number) => ({ x: dir * -48, opacity: 0 }),
};

function newKey() {
  return crypto.randomUUID();
}

/* ---------------- Step 1: choose a payee ---------------- */
function PayeeStep({ onPick }: { onPick: (payee: Payee) => void }) {
  const { data: payees, isPending, isError, refetch } = usePayees();
  const [query, setQuery] = useState("");
  const list = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (payees ?? []).filter((p) => !q || p.nickname.toLowerCase().includes(q) || p.recipient.masked_name.toLowerCase().includes(q));
  }, [payees, query]);

  if (isPending) {
    return (
      <div className="glass space-y-4 rounded-[28px] p-5 shadow-[var(--shadow-soft)]">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex items-center gap-3.5">
            <Skeleton className="size-11 rounded-2xl" />
            <Skeleton className="h-4 flex-1" />
          </div>
        ))}
      </div>
    );
  }
  if (isError) return <LoadError what="your payees" onRetry={() => refetch()} />;

  return (
    <div className="space-y-4">
      {payees.length > 4 && (
        <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search payees" aria-label="Search payees" leading={<Search />} />
      )}
      <div className="glass rounded-[28px] px-5 py-2 shadow-[var(--shadow-soft)]">
        <Link
          href="/payees/new?then=transfer"
          className="-mx-2 flex items-center gap-3.5 rounded-2xl px-2 py-3 transition-colors hover:bg-slate-900/[0.03] dark:hover:bg-white/[0.04]"
        >
          <span className="grid size-11 place-items-center rounded-2xl border-2 border-dashed border-teal-300 text-teal-600 dark:border-teal-400/40 dark:text-teal-300">
            <Plus className="size-5" />
          </span>
          <span className="text-[15px] font-semibold text-teal-700 dark:text-teal-300">New payee</span>
        </Link>
        {list.map((payee) => (
          <PayeeRow key={payee.id} payee={payee} onClick={() => onPick(payee)} />
        ))}
      </div>
      {payees.length === 0 && (
        <EmptyState
          icon={ShieldCheck}
          title="Add someone to pay"
          description="For your safety, Jaga only sends money to saved payees whose name you've checked."
        />
      )}
    </div>
  );
}

/* ---------------- Step 2: amount ---------------- */
function AmountStep({
  payee,
  amount,
  setAmount,
  note,
  setNote,
  balance,
  error,
  onNext,
}: {
  payee: Payee;
  amount: string;
  setAmount: (value: string) => void;
  note: string;
  setNote: (value: string) => void;
  balance: string | undefined;
  error: string | null;
  onNext: () => void;
}) {
  const sen = toSen(amount || "0");
  const tooMuch = balance !== undefined && sen > toSen(balance);
  const valid = sen > BigInt(0) && !tooMuch;
  const [whole, fraction] = amount.split(".");
  const wholeShown = whole ? formatAmount(whole).split(".")[0] : "0";

  // Typing on a real keyboard works too.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.target as HTMLElement).tagName === "INPUT") return;
      if (/^[\d.]$/.test(event.key)) setAmount(pressKey(amount, event.key));
      else if (event.key === "Backspace") setAmount(pressKey(amount, "back"));
      else if (event.key === "Enter" && valid) onNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [amount, setAmount, valid, onNext]);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 rounded-full bg-muted/70 py-1.5 pl-1.5 pr-4">
        <Avatar name={payee.nickname} className="size-9 rounded-full text-[12px]" />
        <div className="min-w-0 text-[13px]">
          <p className="truncate font-bold text-foreground">{payee.nickname}</p>
          <p className="truncate text-muted-foreground">{payee.recipient.masked_number}</p>
        </div>
      </div>

      {/* The big amount. Each new digit pops in. */}
      <div className="py-2 text-center" aria-live="polite">
        <div className={cn("flex items-baseline justify-center gap-1.5 font-extrabold tracking-tight", tooMuch ? "text-rose-500" : "text-foreground")}>
          <span className="text-[22px] text-muted-foreground">RM</span>
          <motion.span
            key={amount}
            initial={{ scale: 0.92, opacity: 0.6 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 600, damping: 26 }}
            className={cn("tabular-nums leading-none", wholeShown.length > 7 ? "text-[44px]" : "text-[56px]", !amount && "text-muted-foreground/40")}
          >
            {wholeShown}
            {fraction !== undefined && <span className="text-[0.6em]">.{fraction}</span>}
          </motion.span>
        </div>
        <p className={cn("mt-2 text-[13px] font-medium", tooMuch ? "text-rose-500" : "text-muted-foreground")}>
          {tooMuch ? "More than your available balance" : balance !== undefined ? `Available ${formatRM(balance)}` : " "}
        </p>
      </div>

      <div className="flex justify-center gap-2">
        {QUICK.map((value) => (
          <motion.button
            key={value}
            type="button"
            whileTap={{ scale: 0.92 }}
            onClick={() => setAmount(value)}
            className={cn(
              "rounded-full px-4 py-2 text-[13px] font-semibold ring-1 transition-colors",
              amount === value
                ? "bg-teal-500 text-white ring-teal-500"
                : "bg-card/60 text-foreground/80 ring-border hover:ring-teal-300 dark:hover:ring-teal-400/40",
            )}
          >
            RM {value}
          </motion.button>
        ))}
      </div>

      <FormAlert message={error} />

      <Input
        value={note}
        maxLength={140}
        onChange={(e) => setNote(e.target.value)}
        placeholder="What's it for? (optional)"
        aria-label="Note"
        leading={<MessageSquareText />}
      />

      <Keypad onKey={(key) => setAmount(pressKey(amount, key))} />

      <Button size="lg" className="w-full" disabled={!valid} onClick={onNext}>
        Continue
      </Button>
    </div>
  );
}

/* ---------------- Step 3: review ---------------- */
function ReviewStep({
  payee,
  amount,
  note,
  fromAccount,
  sending,
  error,
  onSend,
}: {
  payee: Payee;
  amount: string;
  note: string;
  fromAccount: string | undefined;
  sending: boolean;
  error: string | null;
  onSend: () => void;
}) {
  const rows = [
    { label: "From", value: `Jaga Savings ${fromAccount ?? ""}` },
    { label: "To", value: `${payee.recipient.masked_name} · ${payee.recipient.masked_number}` },
    ...(note.trim() ? [{ label: "Note", value: note.trim() }] : []),
    { label: "Arrives", value: "Instantly", icon: Clock },
  ];

  return (
    <div className="space-y-5">
      <div className="glass overflow-hidden rounded-[32px] shadow-[var(--shadow-float)]">
        <div className="bg-gradient-to-br from-teal-400 via-teal-500 to-cyan-600 px-6 pb-6 pt-5 text-center text-white">
          <Avatar name={payee.nickname} className="mx-auto size-14 rounded-full text-[17px] ring-4 ring-white/30" />
          <p className="mt-2 text-[14px] font-medium text-white/85">You&apos;re sending {payee.nickname}</p>
          <p className="mt-1 text-[40px] font-extrabold leading-none tracking-tight tabular-nums">
            <span className="mr-1 text-[20px] text-white/85">RM</span>
            {formatAmount(normalise(amount))}
          </p>
        </div>
        <dl className="divide-y divide-border/70 px-5">
          {rows.map((row) => (
            <div key={row.label} className="flex items-start justify-between gap-4 py-3.5 text-[14px]">
              <dt className="text-muted-foreground">{row.label}</dt>
              <dd className="text-right font-semibold text-foreground">{row.value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="flex gap-3 rounded-2xl bg-gradient-to-r from-teal-50 to-sky-50 p-3.5 text-[13px] leading-relaxed text-teal-900 ring-1 ring-teal-100 dark:from-teal-500/10 dark:to-sky-500/10 dark:text-teal-100 dark:ring-teal-400/15">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-teal-600 dark:text-teal-300" />
        <p>
          Is anyone on the phone telling you to make this transfer? Hang up. Real police, banks and LHDN never ask you to
          move money.
        </p>
      </div>

      <FormAlert message={error} />
      <HoldToSend label="Hold to send" busy={sending} onConfirm={onSend} />
    </div>
  );
}

/* ---------------- The flow ---------------- */
export function TransferFlow() {
  const router = useRouter();
  const params = useSearchParams();
  const presetId = Number(params.get("payee")) || null;
  const { data: payees } = usePayees();
  const { account } = usePrimaryAccount();
  const send = useSendTransfer();

  const [step, setStep] = useState<Step>(presetId ? "amount" : "payee");
  const [direction, setDirection] = useState(1);
  const [payee, setPayee] = useState<Payee | null>(null);
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  // One key per "attempt": kept for retries, renewed when the details change.
  const idempotencyKey = useRef(newKey());

  // Arriving with ?payee=12 (from the payee list): pick them once loaded.
  useEffect(() => {
    if (presetId && !payee && payees) {
      const match = payees.find((p) => p.id === presetId);
      if (match) setPayee(match);
      else setStep("payee");
    }
  }, [presetId, payee, payees]);

  function go(next: Step) {
    setDirection(STEPS.indexOf(next) > STEPS.indexOf(step) ? 1 : -1);
    setError(null);
    if (next === "review") idempotencyKey.current = newKey();
    setStep(next);
  }

  function back() {
    if (step === "payee" || (step === "amount" && presetId)) router.back();
    else go(step === "review" ? "amount" : "payee");
  }

  function submit() {
    if (!payee) return;
    setError(null);
    send.mutate(
      {
        body: { payee_id: payee.id, amount: normalise(amount), note: note.trim() || undefined },
        key: idempotencyKey.current,
      },
      {
        onError: (err) => {
          if (!(err instanceof ApiError)) return setError("Something went wrong. Please try again.");
          if (err.code === "insufficient_funds") {
            go("amount");
            setError(err.message);
          } else if (err.code === "network_error") {
            // Same key on retry: if the first try actually went through, nothing is sent twice.
            setError("Connection lost. Hold again to retry; you won't be charged twice.");
          } else {
            setError(err.message);
          }
        },
      },
    );
  }

  if (send.data) {
    return (
      <TransferSuccess
        transfer={send.data}
        onAgain={() => {
          send.reset();
          setPayee(null);
          setAmount("");
          setNote("");
          setDirection(1);
          setStep("payee");
          router.replace("/transfer");
        }}
      />
    );
  }

  const index = STEPS.indexOf(step);

  return (
    <div>
      <div className="mb-5 flex items-center gap-3">
        <motion.button
          type="button"
          whileTap={{ scale: 0.9 }}
          onClick={back}
          aria-label="Back"
          className="glass grid size-11 shrink-0 place-items-center rounded-full text-foreground/70 shadow-[var(--shadow-soft)] transition hover:text-foreground"
        >
          <ArrowLeft className="size-5" />
        </motion.button>
        {/* Progress: three segments that fill as you go. */}
        <div className="flex flex-1 gap-1.5" aria-label={`Step ${index + 1} of 3`}>
          {STEPS.map((s, i) => (
            <div key={s} className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-teal-400 to-teal-600"
                initial={false}
                animate={{ width: i <= index ? "100%" : "0%" }}
                transition={{ type: "spring", stiffness: 200, damping: 30 }}
              />
            </div>
          ))}
        </div>
      </div>

      <AnimatePresence mode="popLayout" custom={direction} initial={false}>
        <motion.div
          key={step}
          custom={direction}
          variants={slide}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ type: "spring", stiffness: 380, damping: 36 }}
        >
          <h1 className="mb-5 text-[28px] font-extrabold tracking-tight text-foreground">{TITLES[step]}</h1>

          {step === "payee" && (
            <PayeeStep
              onPick={(picked) => {
                setPayee(picked);
                go("amount");
              }}
            />
          )}
          {step === "amount" &&
            (payee ? (
              <AmountStep
                payee={payee}
                amount={amount}
                setAmount={(value) => {
                  setAmount(value);
                  setError(null);
                }}
                note={note}
                setNote={setNote}
                balance={account?.balance}
                error={error}
                onNext={() => go("review")}
              />
            ) : (
              <Skeleton className="h-[480px] w-full rounded-[28px]" />
            ))}
          {step === "review" && payee && (
            <ReviewStep
              payee={payee}
              amount={amount}
              note={note}
              fromAccount={account?.masked_number}
              sending={send.isPending}
              error={error}
              onSend={submit}
            />
          )}
        </motion.div>
      </AnimatePresence>

    </div>
  );
}
