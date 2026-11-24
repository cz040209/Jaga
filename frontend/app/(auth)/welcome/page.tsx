import type { Metadata } from "next";

import { Welcome } from "@/features/auth/Welcome";

export const metadata: Metadata = { title: "Welcome" };

export default function WelcomePage() {
  return <Welcome />;
}
