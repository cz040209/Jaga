import { BankShell } from "@/components/layout/BankShell";

/** Every logged-in bank screen: login guard + phone column + bottom navigation. */
export default function BankLayout({ children }: { children: React.ReactNode }) {
  return <BankShell>{children}</BankShell>;
}
