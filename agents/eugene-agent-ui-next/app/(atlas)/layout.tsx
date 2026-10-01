import { redirect } from "next/navigation";
import { currentUser } from "@/lib/atlas/auth";
import { AtlasShell } from "@/components/atlas/AtlasShell";

export const dynamic = "force-dynamic";

export default async function AtlasLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await currentUser();
  if (!user) redirect("/login");
  return <AtlasShell user={user}>{children}</AtlasShell>;
}
