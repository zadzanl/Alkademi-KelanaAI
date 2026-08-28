import Link from "next/link";
import { getCurrentUser } from "../services/authService";
import { logoutFormAction } from "../app/actions";

export async function AuthHeader() {
  const user = await getCurrentUser();
  return user ? <div className="flex items-center gap-3 text-sm"><span className="text-muted-ink">{user.username}</span><form action={logoutFormAction}><button className="font-bold text-terracotta-dark underline">Sign out</button></form></div> : <Link href="/auth" className="font-bold text-terracotta-dark">Sign in</Link>;
}