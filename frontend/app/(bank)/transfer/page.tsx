import type { Metadata } from "next";
import { Suspense } from "react";

import { TransferFlow } from "@/features/transfers/TransferFlow";

export const metadata: Metadata = { title: "Transfer" };

export default function Page() {
  // Suspense: the flow reads ?payee= from the URL.
  return (
    <Suspense>
      <TransferFlow />
    </Suspense>
  );
}
