import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { greeting } from "@/lib/atlas/request";

export const runtime = "nodejs";

export async function GET() {
  const user = await currentUser();
  if (!user) {
    return NextResponse.json({ user: null }, { status: 401 });
  }
  return NextResponse.json({ user, greeting: greeting(user.name) });
}
