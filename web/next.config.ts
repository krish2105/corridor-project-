import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // There is an unrelated package-lock.json in the home directory. Without this,
  // Next.js infers the workspace root from it and warns on every start.
  outputFileTracingRoot: path.join(__dirname),
  // `npm run build:local` writes to .next-build so a local production build cannot
  // clobber the cache of a dev server that happens to be running - that leaves a stale
  // React Client Manifest and the dev server starts returning 500s.
  // Never applied on Vercel, which expects .next and fails the deploy without it.
  distDir: process.env.VERCEL ? ".next" : (process.env.NEXT_DIST_DIR || ".next"),
};

export default nextConfig;
