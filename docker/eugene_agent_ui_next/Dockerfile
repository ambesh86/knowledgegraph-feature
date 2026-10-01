# syntax=docker/dockerfile:1.6
# --------------------------------------------------------------------------
# Eugene Agent UI (Next.js 14) — multi-stage build
# --------------------------------------------------------------------------
FROM node:20-bookworm-slim AS deps
WORKDIR /app
# Trust the corporate TLS-inspection root CA (e.g. Zscaler) so npm can reach
# hosts that aren't on the proxy's SSL-bypass list. No-op outside that network.
COPY docker/certs/zscaler-root-ca.crt /usr/local/share/ca-certificates/zscaler-root-ca.crt
RUN apt-get update -y && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates && rm -rf /var/lib/apt/lists/*
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
COPY agents/eugene-agent-ui-next/package.json ./
# no lockfile committed — let npm resolve and cache
RUN --mount=type=cache,target=/root/.npm \
    npm install --no-audit --no-fund

FROM node:20-bookworm-slim AS builder
WORKDIR /app
# Path prefix the app is served under behind the ALB (e.g. /nextgen). Drives
# both next.config.js basePath and the client-inlined NEXT_PUBLIC_BASE_PATH.
# Override at build: --build-arg NEXT_BASE_PATH=/your-path  (empty = root)
ARG NEXT_BASE_PATH=/nextgen
# Give the Next.js production build enough V8 heap. The default old-space limit
# OOMs ("Fatal error … line 0") on this app under Docker memory pressure.
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_BASE_PATH=$NEXT_BASE_PATH \
    NODE_OPTIONS=--max-old-space-size=4096
COPY --from=deps /app/node_modules ./node_modules
COPY agents/eugene-agent-ui-next/ .
RUN npm run build

FROM node:20-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=18502 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 --ingroup nodejs nextjs

# Standalone output bundles only what is needed for runtime
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 18502
CMD ["node", "server.js"]
