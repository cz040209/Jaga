import type { Metadata } from "next";

import { HomeScreen } from "@/features/accounts/HomeScreen";

export const metadata: Metadata = { title: "Home" };

export default function HomePage() {
  return <HomeScreen />;
}
