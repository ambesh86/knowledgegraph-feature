import { defineConfig, devices } from "@playwright/test";

/**
 * E2E test config for the CSL Atlas UI. Runs against the deployed Docker UI at
 * http://localhost:18502/nextgen (override with ATLAS_BASE_URL). Tests seed data
 * through the API and drive the browser to verify behavior end-to-end.
 */
// Trailing slash is REQUIRED so relative paths ("login", "api/…") resolve under
// the /nextgen basePath. A leading-slash path would drop the basePath.
const RAW = process.env.ATLAS_BASE_URL ?? "http://localhost:18502/nextgen";
const BASE_URL = RAW.endsWith("/") ? RAW : `${RAW}/`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    actionTimeout: 15_000,
  },
  projects: [
    // Use the system Google Chrome (bundled chromium isn't downloaded here).
    { name: "chromium", use: { ...devices["Desktop Chrome"], channel: "chrome" } },
  ],
});
