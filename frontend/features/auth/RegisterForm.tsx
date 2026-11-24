"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Mail, Smartphone, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { AuthCard, FormAlert } from "@/features/auth/AuthCard";
import { useAuth } from "@/features/auth/AuthProvider";
import { PasswordInput } from "@/features/auth/PasswordInput";
import { registerSchema, type RegisterValues } from "@/features/auth/schemas";
import { StrengthMeter } from "@/features/auth/StrengthMeter";
import { ApiError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "ms", label: "Bahasa" },
  { value: "zh", label: "中文" },
] as const;

const FIELDS = ["full_name", "email", "phone_number", "password", "preferred_language"] as const;

export function RegisterForm() {
  const { register: createAccount } = useAuth();
  const router = useRouter();
  const [alert, setAlert] = useState<string | null>(null);

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: "",
      email: "",
      phone_number: "",
      password: "",
      preferred_language: "en",
    },
  });
  const { errors, isSubmitting } = form.formState;
  const password = form.watch("password");

  const onSubmit = form.handleSubmit(async (values) => {
    setAlert(null);
    try {
      await createAccount(values);
      toast.success("Your account is ready", {
        description: "RM 10,000.00 of demo money is waiting for you.",
      });
      router.replace("/home");
    } catch (error) {
      if (!(error instanceof ApiError)) {
        setAlert("Something went wrong. Please try again.");
        return;
      }
      if (error.code === "email_taken") {
        form.setError("email", { message: error.message });
      } else if (error.code === "phone_taken") {
        form.setError("phone_number", { message: error.message });
      } else if (error.code === "validation_error") {
        // Backend found something the form didn't: show it on the right field.
        let shown = false;
        for (const field of FIELDS) {
          const message = error.fieldErrors[field];
          if (message) {
            form.setError(field, { message });
            shown = true;
          }
        }
        if (!shown) setAlert(error.message);
      } else {
        setAlert(error.message);
      }
    }
  });

  return (
    <AuthCard
      title="Create your account"
      subtitle="It takes a minute. You'll start with RM 10,000 of demo money to try everything."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-primary hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <FormAlert message={alert} />

        <Field label="Full name" htmlFor="full_name" error={errors.full_name?.message}>
          <Input
            id="full_name"
            autoComplete="name"
            placeholder="As on your MyKad"
            leading={<UserRound />}
            invalid={!!errors.full_name}
            {...form.register("full_name")}
          />
        </Field>

        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            inputMode="email"
            placeholder="you@example.com"
            leading={<Mail />}
            invalid={!!errors.email}
            {...form.register("email")}
          />
        </Field>

        <Field label="Mobile number" htmlFor="phone_number" error={errors.phone_number?.message}>
          <Input
            id="phone_number"
            type="tel"
            autoComplete="tel"
            inputMode="tel"
            placeholder="012-345 6789"
            leading={<Smartphone />}
            invalid={!!errors.phone_number}
            {...form.register("phone_number")}
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          error={errors.password?.message}
          hint={<StrengthMeter password={password} />}
        >
          <PasswordInput
            id="password"
            autoComplete="new-password"
            placeholder="Create a password"
            invalid={!!errors.password}
            {...form.register("password")}
          />
        </Field>

        <Controller
          control={form.control}
          name="preferred_language"
          render={({ field }) => (
            <fieldset className="space-y-2">
              <legend className="text-[13px] font-semibold text-foreground/80">
                Message language
              </legend>
              <div className="grid grid-cols-3 gap-1 rounded-2xl bg-muted p-1">
                {LANGUAGES.map((language) => {
                  const selected = field.value === language.value;
                  return (
                    <button
                      key={language.value}
                      type="button"
                      onClick={() => field.onChange(language.value)}
                      aria-pressed={selected}
                      className={cn(
                        "relative h-11 rounded-xl text-[14px] font-semibold transition-colors",
                        selected ? "text-teal-700 dark:text-teal-300" : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {/* One white pill that slides to the chosen language. */}
                      {selected && (
                        <motion.span
                          layoutId="language-pill"
                          className="absolute inset-0 rounded-xl bg-card shadow-sm"
                          transition={{ type: "spring", stiffness: 450, damping: 34 }}
                        />
                      )}
                      <span className="relative">{language.label}</span>
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}
        />

        <Button type="submit" size="lg" className="w-full" loading={isSubmitting}>
          {isSubmitting ? "Creating your account" : "Create account"}
        </Button>

        <p className="text-center text-[12.5px] leading-relaxed text-muted-foreground/80">
          Jaga is a demo bank: no real money, no real bank details.
        </p>
      </form>
    </AuthCard>
  );
}
