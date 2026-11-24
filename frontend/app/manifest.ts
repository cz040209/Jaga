import type { MetadataRoute } from "next";

/**
 * The Web App Manifest (served at /manifest.webmanifest). It's what lets a
 * phone install Jaga to the home screen and open it full-screen, with its own
 * icon and splash colour, like a native app.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Jaga: scam-safe banking",
    short_name: "Jaga",
    description: "The bank that guards you against scams in real time.",
    start_url: "/home",
    scope: "/",
    display: "standalone", // no browser address bar
    orientation: "portrait",
    background_color: "#f6f8fa", // splash screen while the app starts
    theme_color: "#f6f8fa",
    categories: ["finance"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      // Full-bleed version: Android crops it into a circle, squircle, etc.
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
