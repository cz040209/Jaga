"use client";

import { motion } from "framer-motion";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { LogoMark } from "@/components/brand/Logo";
import { BottomNav } from "@/components/layout/BottomNav";
import { useAuth } from "@/features/auth/AuthProvider";

/**
 * Frame for every logged-in bank screen: a phone-width column (centred on
 * desktop), the bottom navigation, and the login guard. Until we know the
 * session is valid, it shows a calm breathing logo instead of empty UI.
 */
export function BankShell({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  // Step-by-step flows get the whole screen: no tab bar to tap away by accident.
  const focused = pathname === "/transfer" || pathname.startsWith("/payees/new");

  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  if (status !== "authenticated") {
    return (
      <div className="grid min-h-dvh place-items-center">
        <motion.div
          animate={{ scale: [1, 1.08, 1], opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        >
          <LogoMark className="size-16 drop-shadow-[0_10px_20px_rgb(13_148_136/0.35)]" />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="mx-auto min-h-dvh max-w-md">
      <main className={`px-5 pt-[max(20px,env(safe-area-inset-top))] ${focused ? "pb-10" : "pb-36"}`}>
        {children}
      </main>
      {!focused && <BottomNav />}
    </div>
  );
}
