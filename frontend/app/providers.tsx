"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import { useState } from "react";
import { Toaster } from "sonner";

import { ThemeProvider, useTheme } from "@/components/theme/ThemeProvider";
import { AuthProvider } from "@/features/auth/AuthProvider";
import { ApiError } from "@/lib/api/errors";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000, // data counts as fresh for 30 s: no refetch storm when switching tabs
        retry: (failures, error) => {
          // 4xx won't fix itself on retry (not found, not allowed, ...); network blips might.
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
          return failures < 2;
        },
      },
    },
  });
}

function ThemedToaster() {
  const { resolvedTheme } = useTheme();
  return (
    <Toaster
      position="top-center"
      richColors
      theme={resolvedTheme}
      toastOptions={{ className: "!rounded-2xl !font-sans" }}
    />
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(makeQueryClient);
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        {/* "user": if the phone asks for reduced motion, animations become simple fades. */}
        <MotionConfig reducedMotion="user">
          <AuthProvider>{children}</AuthProvider>
        </MotionConfig>
        <ThemedToaster />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
