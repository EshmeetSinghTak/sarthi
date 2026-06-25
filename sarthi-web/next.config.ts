import type { NextConfig } from "next";

const BACKEND = process.env.SARTHI_BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Proxy the agent API under the app's own origin. Keeps the identity cookie
  // first-party and removes browser-side CORS concerns.
  async rewrites() {
    return [{ source: "/api/agent/:path*", destination: `${BACKEND}/:path*` }];
  },
};

export default nextConfig;
