/**
 * Client-safe base path.
 *
 * Mirrors `basePath` in next.config.js so raw `fetch("/api/...")` calls land
 * under the ALB path rule (e.g. `/nextgen/*`). Next.js auto-prefixes `/_next/`
 * assets and next/link/Image, but NOT manual fetch() — so every absolute
 * fetch to our own route handlers must go through `apiPath()`.
 *
 * Set at build time via NEXT_PUBLIC_BASE_PATH (inlined into the client bundle).
 * Empty string = served at root, no prefix.
 */
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** Prefix an absolute app path with the configured base path. */
export const apiPath = (path: string): string => `${BASE_PATH}${path}`;
