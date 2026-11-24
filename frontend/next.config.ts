import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A second, temporary server (e.g. for automated screenshots) can build into
  // its own folder with NEXT_DIST_DIR=.next-shot, so it never disturbs `pnpm dev`.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
