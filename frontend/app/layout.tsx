import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";

import { MeshBackground } from "@/components/layout/MeshBackground";
import { themeScript } from "@/components/theme/ThemeProvider";
import { Providers } from "./providers";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Jaga", template: "%s · Jaga" },
  description: "Jaga: the bank that guards you against scams in real time.",
  applicationName: "Jaga",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#f6f8fa", // ThemeProvider swaps this when the theme changes
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning: the theme script edits <html> before React loads.
    <html lang="en" className={jakarta.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <MeshBackground />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
