import type { Metadata } from "next";

import { ReceiptScreen } from "@/features/transfers/ReceiptScreen";

export const metadata: Metadata = { title: "Receipt" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReceiptScreen id={Number(id) || 0} />;
}
