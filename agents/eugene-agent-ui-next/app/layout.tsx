import type { Metadata, Viewport } from "next";
import { Providers } from "./providers";
import { apiPath } from "@/lib/basePath";
import "./globals.css";

export const metadata: Metadata = {
  title: "CSL · Ask · Research · Decide",
  description:
    "CSL business-development intelligence workspace: graph-grounded research, competitive monitoring, and decision-ready briefs.",
  // Base-path aware. Next prefixes next/link and /_next assets automatically but NOT
  // metadata icon paths, so a bare "/favicon.svg" resolved to the ALB root and 404'd
  // on every page load when the app is served under /nextgen.
  icons: { icon: apiPath("/favicon.svg") },
};

export const viewport: Viewport = {
  themeColor: "#07090f",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
