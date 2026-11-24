"use client";

import { motion } from "framer-motion";

/**
 * Next.js re-creates a template on every navigation (a layout is kept),
 * so this gives each bank screen a soft glide-in when you move between tabs.
 */
export default function BankTemplate({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
    >
      {children}
    </motion.div>
  );
}
