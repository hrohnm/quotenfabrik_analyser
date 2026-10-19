import type { NextConfig } from "next";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Browser requests to /api/* are proxied to the FastAPI backend (no CORS setup needed).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
  images: { remotePatterns: [{ protocol: "https", hostname: "media.api-sports.io" }] },
};

export default nextConfig;
