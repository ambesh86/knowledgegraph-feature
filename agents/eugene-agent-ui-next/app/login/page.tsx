import { redirect } from "next/navigation";
import { currentUser } from "@/lib/atlas/auth";
import { LoginForm } from "@/components/atlas/LoginForm";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const user = await currentUser();
  if (user) redirect("/today");
  return <LoginForm />;
}
