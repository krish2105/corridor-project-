import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // There is an unrelated package-lock.json in the home directory. Without this,
  // Next.js infers the workspace root from it and warns on every start.
  outputFileTracingRoot: path.join(__dirname),
  // `npm run build` writes to .next-build so a production build can never clobber
  // the cache of a dev server that happens to be running. Doing so leaves a stale
  // React Client Manifest and the dev server starts returning 500s.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
