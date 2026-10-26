import Link from "next/link";
import type { ReactNode } from "react";

/** Link to the team page (not for use inside another link, e.g. a whole fixture row). */
export function TeamLink({ id, children, className = "" }: { id: number; children: ReactNode; className?: string }) {
  return (
    <Link href={`/team/${id}`} className={`hover:underline hover:decoration-slate-300 hover:underline-offset-4 ${className}`}>
      {children}
    </Link>
  );
}
