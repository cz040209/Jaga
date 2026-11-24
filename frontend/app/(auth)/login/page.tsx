import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/features/auth/LoginForm";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage() {
  // LoginForm reads ?next=..., which Next.js requires inside a Suspense boundary.
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
