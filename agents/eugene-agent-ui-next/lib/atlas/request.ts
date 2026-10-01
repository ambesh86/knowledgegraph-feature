/** Extract client IP + user-agent from a Next.js route-handler Request. */
export function clientMeta(req: Request): { ip: string; userAgent: string } {
  const h = req.headers;
  const fwd = h.get("x-forwarded-for");
  const ip = (fwd ? fwd.split(",")[0] : h.get("x-real-ip") ?? "").trim() || "unknown";
  const userAgent = h.get("user-agent") ?? "unknown";
  return { ip, userAgent };
}

/** Friendly time-of-day greeting in the server's locale. */
export function greeting(name: string, date = new Date()): string {
  const h = date.getHours();
  const part = h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
  return `Good ${part}, ${name.split(" ")[0]}`;
}
