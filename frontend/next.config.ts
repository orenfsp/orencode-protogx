import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.resolve(__dirname),
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [{ source: "/api/:path*/", destination: `${process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000"}/api/:path*/` }];
  },
};

export default nextConfig;
