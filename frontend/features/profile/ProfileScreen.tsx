"use client";

import { motion } from "framer-motion";
import {
  ChevronRight,
  Globe,
  KeyRound,
  Laptop,
  LogOut,
  Mail,
  MonitorSmartphone,
  PencilLine,
  Smartphone,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Avatar } from "@/components/shared/Avatar";
import { ThemePicker } from "@/components/theme/ThemePicker";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { FormAlert } from "@/features/auth/AuthCard";
import { useAuth } from "@/features/auth/AuthProvider";
import { PasswordInput } from "@/features/auth/PasswordInput";
import { StrengthMeter } from "@/features/auth/StrengthMeter";
import { useChangePassword, useDevices, useProfile, useSessions, useUpdateProfile } from "@/features/profile/hooks";
import { ApiError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import type { Customer, Language } from "@/types";

const LANGUAGES: { value: Language; label: string; full: string }[] = [
  { value: "en", label: "English", full: "English" },
  { value: "ms", label: "Bahasa", full: "Bahasa Melayu" },
  { value: "zh", label: "中文", full: "中文" },
];

/* ---------- Building blocks ---------- */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 px-1 text-[12px] font-bold uppercase tracking-wider text-muted-foreground">{title}</h2>
      <div className="glass divide-y divide-border/60 rounded-[28px] px-5 shadow-[var(--shadow-soft)]">{children}</div>
    </section>
  );
}

function InfoRow({ icon: Icon, label, value }: { icon: typeof Mail; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3.5 py-3.5">
      <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-muted text-foreground/70">
        <Icon className="size-5" />
      </span>
      <div className="min-w-0">
        <p className="text-[12.5px] text-muted-foreground">{label}</p>
        <p className="truncate text-[15px] font-semibold text-foreground">{value}</p>
      </div>
    </div>
  );
}

function NavRow({
  icon: Icon,
  label,
  hint,
  href,
  onClick,
  chip,
}: {
  icon: typeof Mail;
  label: string;
  hint?: string;
  href?: string;
  onClick?: () => void;
  chip: string;
}) {
  const inner = (
    <>
      <span className={cn("grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br text-white shadow-sm", chip)}>
        <Icon className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-semibold text-foreground">{label}</span>
        {hint && <span className="block text-[12.5px] text-muted-foreground">{hint}</span>}
      </span>
      <ChevronRight className="size-4 text-muted-foreground/60 transition-transform group-hover:translate-x-0.5" />
    </>
  );
  const className = "group flex w-full items-center gap-3.5 py-3.5 text-left";
  return href ? (
    <Link href={href} className={className}>
      {inner}
    </Link>
  ) : (
    <button type="button" onClick={onClick} className={className}>
      {inner}
    </button>
  );
}

/* ---------- Sheets ---------- */

function EditProfileForm({ profile, onDone }: { profile: Customer; onDone: () => void }) {
  const [name, setName] = useState(profile.full_name);
  const [language, setLanguage] = useState<Language>(profile.preferred_language as Language);
  const [error, setError] = useState<string | null>(null);
  const update = useUpdateProfile();
  const trimmed = name.trim().replace(/\s+/g, " ");

  return (
    <form
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        if (trimmed.length < 2) return setError("Enter your full name.");
        const body = {
          ...(trimmed !== profile.full_name ? { full_name: trimmed } : {}),
          ...(language !== profile.preferred_language ? { preferred_language: language } : {}),
        };
        if (Object.keys(body).length === 0) return onDone();
        update.mutate(body, {
          onSuccess: () => {
            toast.success("Profile updated");
            onDone();
          },
          onError: (err) => setError(err instanceof ApiError ? err.message : "Couldn't save. Please try again."),
        });
      }}
    >
      <FormAlert message={error} />
      <Field label="Full name" htmlFor="edit_name">
        <Input id="edit_name" value={name} maxLength={200} onChange={(e) => setName(e.target.value)} leading={<UserRound />} />
      </Field>
      <fieldset className="space-y-2">
        <legend className="text-[13px] font-semibold text-foreground/80">Message language</legend>
        <div className="grid grid-cols-3 gap-1 rounded-2xl bg-muted p-1">
          {LANGUAGES.map((option) => {
            const selected = language === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={selected}
                onClick={() => setLanguage(option.value)}
                className={cn(
                  "relative h-11 rounded-xl text-[14px] font-semibold transition-colors",
                  selected ? "text-teal-700 dark:text-teal-300" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {selected && (
                  <motion.span
                    layoutId="edit-language-pill"
                    className="absolute inset-0 rounded-xl bg-card shadow-sm"
                    transition={{ type: "spring", stiffness: 450, damping: 34 }}
                  />
                )}
                <span className="relative">{option.label}</span>
              </button>
            );
          })}
        </div>
        <p className="text-[12.5px] text-muted-foreground">Alerts in your inbox will use this language.</p>
      </fieldset>
      <Button type="submit" size="lg" className="w-full" loading={update.isPending}>
        Save changes
      </Button>
    </form>
  );
}

function ChangePasswordForm({ onDone }: { onDone: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<{ current?: string; next?: string; confirm?: string; form?: string }>({});
  const change = useChangePassword();

  return (
    <form
      className="space-y-5"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const found: typeof errors = {};
        if (!current) found.current = "Enter your current password";
        if (next.length < 8) found.next = "Use at least 8 characters";
        else if (next.trim() !== next) found.next = "Password can't start or end with a space";
        if (confirm !== next) found.confirm = "Passwords don't match";
        setErrors(found);
        if (Object.keys(found).length) return;
        change.mutate(
          { current_password: current, new_password: next },
          {
            onSuccess: ({ revoked_sessions }) => {
              toast.success("Password changed", {
                description: revoked_sessions
                  ? `Signed out ${revoked_sessions} other device${revoked_sessions === 1 ? "" : "s"} for safety.`
                  : "You're still signed in here.",
              });
              onDone();
            },
            onError: (err) => {
              if (err instanceof ApiError && err.code === "invalid_password") setErrors({ current: err.message });
              else if (err instanceof ApiError && err.code === "password_unchanged") setErrors({ next: err.message });
              else if (err instanceof ApiError && err.fieldErrors.new_password) setErrors({ next: err.fieldErrors.new_password });
              else setErrors({ form: err instanceof ApiError ? err.message : "Couldn't change it. Please try again." });
            },
          },
        );
      }}
    >
      <FormAlert message={errors.form ?? null} />
      <Field label="Current password" htmlFor="current_password" error={errors.current}>
        <PasswordInput id="current_password" autoComplete="current-password" value={current} invalid={!!errors.current} onChange={(e) => setCurrent(e.target.value)} />
      </Field>
      <Field label="New password" htmlFor="new_password" error={errors.next} hint={<StrengthMeter password={next} />}>
        <PasswordInput id="new_password" autoComplete="new-password" value={next} invalid={!!errors.next} onChange={(e) => setNext(e.target.value)} />
      </Field>
      <Field label="Confirm new password" htmlFor="confirm_password" error={errors.confirm}>
        <PasswordInput id="confirm_password" autoComplete="new-password" value={confirm} invalid={!!errors.confirm} onChange={(e) => setConfirm(e.target.value)} />
      </Field>
      <p className="text-[12.5px] leading-relaxed text-muted-foreground">
        Other devices will be signed out. This one stays signed in.
      </p>
      <Button type="submit" size="lg" className="w-full" loading={change.isPending}>
        Change password
      </Button>
    </form>
  );
}

/* ---------- Screen ---------- */

export function ProfileScreen() {
  const { data: profile } = useProfile();
  const { data: devices } = useDevices();
  const { data: sessions } = useSessions();
  const { logout } = useAuth();
  const [leaving, setLeaving] = useState(false);
  const [sheet, setSheet] = useState<"edit" | "password" | null>(null);
  const [lastSheet, setLastSheet] = useState<"edit" | "password">("edit"); // keeps content during the close animation

  const openSheet = (which: "edit" | "password") => {
    setLastSheet(which);
    setSheet(which);
  };
  const closeSheet = () => setSheet(null);

  return (
    <div className="space-y-6">
      <h1 className="text-[28px] font-extrabold tracking-tight text-foreground">Profile</h1>

      {/* Identity card */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass flex items-center gap-4 rounded-[28px] p-5 shadow-[var(--shadow-soft)]"
      >
        {profile ? (
          <>
            <Avatar name={profile.full_name} className="size-16 rounded-[22px] text-[20px] shadow-[var(--shadow-glow)]" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[19px] font-bold text-foreground">{profile.full_name}</p>
              <p className="text-[13px] text-muted-foreground">
                Member since{" "}
                {new Date(profile.created_at).toLocaleDateString("en-MY", { month: "long", year: "numeric" })}
              </p>
            </div>
            <motion.button
              type="button"
              whileTap={{ scale: 0.9 }}
              onClick={() => openSheet("edit")}
              aria-label="Edit profile"
              className="grid size-11 shrink-0 place-items-center rounded-full bg-muted text-foreground/70 transition hover:text-foreground"
            >
              <PencilLine className="size-5" />
            </motion.button>
          </>
        ) : (
          <>
            <Skeleton className="size-16 rounded-[22px]" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </>
        )}
      </motion.section>

      <Section title="Details">
        {profile ? (
          <>
            <InfoRow icon={Mail} label="Email" value={profile.email} />
            <InfoRow icon={Smartphone} label="Mobile" value={profile.phone_number} />
            <InfoRow
              icon={Globe}
              label="Message language"
              value={LANGUAGES.find((l) => l.value === profile.preferred_language)?.full ?? profile.preferred_language}
            />
          </>
        ) : (
          <div className="space-y-3 py-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        )}
      </Section>

      <Section title="Security">
        <NavRow icon={KeyRound} label="Change password" hint="Signs out your other devices" chip="from-violet-400 to-indigo-500" onClick={() => openSheet("password")} />
        <NavRow
          icon={Laptop}
          label="Devices"
          hint={devices ? `${devices.length} device${devices.length === 1 ? "" : "s"} used to sign in` : "Phones and computers you use"}
          chip="from-sky-400 to-blue-500"
          href="/profile/devices"
        />
        <NavRow
          icon={MonitorSmartphone}
          label="Active sessions"
          hint={sessions ? `${sessions.length} signed in` : "Where you're signed in"}
          chip="from-teal-400 to-teal-600"
          href="/profile/sessions"
        />
      </Section>

      <section className="space-y-3">
        <div className="px-1">
          <h2 className="text-[12px] font-bold uppercase tracking-wider text-muted-foreground">Appearance</h2>
          <p className="text-[13px] text-muted-foreground">System follows your phone&apos;s light or dark setting.</p>
        </div>
        <ThemePicker />
      </section>

      <Button
        variant="outline"
        size="lg"
        className="w-full text-destructive hover:bg-destructive/10"
        loading={leaving}
        onClick={async () => {
          setLeaving(true);
          await logout();
        }}
      >
        <LogOut /> Log out
      </Button>

      <Sheet
        open={sheet !== null}
        onClose={closeSheet}
        title={lastSheet === "edit" ? "Edit profile" : "Change password"}
        description={lastSheet === "password" ? "Use one you don't use anywhere else." : undefined}
      >
        {lastSheet === "edit" && profile && <EditProfileForm key={String(sheet)} profile={profile} onDone={closeSheet} />}
        {lastSheet === "password" && <ChangePasswordForm key={String(sheet)} onDone={closeSheet} />}
      </Sheet>
    </div>
  );
}
