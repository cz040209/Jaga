import type { Metadata } from "next";

import { SessionsScreen } from "@/features/profile/SessionsScreen";

export const metadata: Metadata = { title: "Active sessions" };

export default function Page() {
  return <SessionsScreen />;
}
