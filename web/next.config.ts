import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // There is an unrelated package-lock.json in the home directory. Without this,
  // Next.js infers the workspace root from it and warns on every start.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
