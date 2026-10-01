/** @type {import('next').NextConfig} */
// Path prefix the app is served under (e.g. "/nextgen" behind an ALB path
// rule). Empty = served at root. Must match lib/basePath.ts, so both read the
// same NEXT_PUBLIC_BASE_PATH build-time env var.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig = {
  output: "standalone",
  ...(basePath ? { basePath } : {}),
  reactStrictMode: true,
  // Cytoscape plugins are ESM-only
  transpilePackages: ["cytoscape-cola", "cytoscape-cxtmenu", "cytoscape-dagre"],
  experimental: {
    // Allow large SSE responses without buffering
    proxyTimeout: 600_000,
  },
  env: {
    NEXT_PUBLIC_APP_NAME: "Eugene",
  },
};

module.exports = nextConfig;
