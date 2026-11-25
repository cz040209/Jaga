import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A second, temporary server (e.g. for automated screenshots) can build into
  // its own folder with NEXT_DIST_DIR=.next-shot, so it never disturbs `pnpm dev`.
  distDir: process.env.NEXT_DIST_DIR || ".next",

  // The Docker image builds a "standalone" server (only the files it needs to
  // run, no full node_modules). Normal `pnpm dev` / `pnpm build` are unchanged.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,

  // Dev only: allow opening the dev server from a phone on the same Wi-Fi
  // (192.168.x.x / 10.x.x.x) or through a Cloudflare tunnel.
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "172.*.*.*", "*.trycloudflare.com"],

  // Next.js 15 "streams" <head> tags (manifest, iPhone app tags) into the page
  // body for normal browsers, where Chrome and iOS ignore them, so the app
  // can't be installed. Matching every user agent keeps them in <head>.
  htmlLimitedBots: /.*/,

  async headers() {
    return [
      {
        // The browser must always check for a new service worker.
        source: "/sw.js",
        headers: [
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
        ],
      },
    ];
  },
};

export default nextConfig;
