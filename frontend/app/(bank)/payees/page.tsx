import type { Metadata } from "next";

import { PayeesScreen } from "@/features/payees/PayeesScreen";

export const metadata: Metadata = { title: "Payees" };

export default function Page() {
  return <PayeesScreen />;
}
