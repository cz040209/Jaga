"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Mail } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { AuthCard, FormAlert } from "@/features/auth/AuthCard";
import { useAuth } from "@/features/auth/AuthProvider";
import { PasswordInput } from "@/features/auth/PasswordInput";
import { loginSchema, type LoginValues } from "@/features/auth/schemas";
import { ApiError } from "@/lib/api/errors";

/** Only follow `?next=` to our own pages ("/history"), never to another site. */
function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/home";
}

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [alert, setAlert] = useState<string | null>(null);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (values) => {
    setAlert(null);
    try {
      const { customer, is_new_device } = await login(values);
      if (is_new_device) {
        toast.info("New device signed in", {
          description: "We've sent a security alert to your inbox, just in case.",
        });
      } else {
        toast.success(`Welcome back, ${customer.full_name.split(" ")[0]}`);
      }
      router.replace(safeNext(searchParams.get("next")));
    } catch (error) {
      if (error instanceof ApiError) {
        // invalid_credentials, account_not_active, device_blocked, network_error...
        setAlert(error.message);
      } else {
        setAlert("Something went wrong. Please try again.");
      }
    }
  });

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Log in to check your balance, send money and stay protected."
      footer={
        <>
          New to Jaga?{" "}
          <Link href="/register" className="font-semibold text-primary hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <FormAlert message={alert} />

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

        <Field label="Password" htmlFor="password" error={errors.password?.message}>
          <PasswordInput
            id="password"
            autoComplete="current-password"
            placeholder="Your password"
            invalid={!!errors.password}
            {...form.register("password")}
          />
        </Field>

        <Button type="submit" size="lg" className="w-full" loading={isSubmitting}>
          {isSubmitting ? "Logging in" : "Log in"}
        </Button>
      </form>
    </AuthCard>
  );
}
