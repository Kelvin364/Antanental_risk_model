import type { NextConfig } from "next";

// The production build is a static export that FastAPI serves from
// frontend/out, so the interface and the API share one origin. During
// `npm run dev` the API calls are forwarded to a local uvicorn instead.
const api = process.env.ANTENATAL_API_URL ?? "http://127.0.0.1:8000";
const dev = process.env.NODE_ENV === "development";

const config: NextConfig = {
  output: dev ? undefined : "export",
  trailingSlash: true,
  images: { unoptimized: true },
  ...(dev && {
    // API paths have no trailing slash; keep Next from adding one before forwarding.
    skipTrailingSlashRedirect: true,
    async rewrites() {
      return [
        { source: "/api/:path*", destination: `${api}/api/:path*` },
        { source: "/health", destination: `${api}/health` },
      ];
    },
  }),
};

export default config;
