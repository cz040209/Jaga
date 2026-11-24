import type { Metadata } from "next";
import { Suspense } from "react";

import { AddPayeeScreen } from "@/features/payees/AddPayeeScreen";

export const metadata: Metadata = { title: "Add payee" };

export default function Page() {
  // Suspense: the screen reads ?then=transfer from the URL.
  return (
    <Suspense>
      <AddPayeeScreen />
    </Suspense>
  );
}
