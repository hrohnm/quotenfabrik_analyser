import Link from "next/link";
import type { ReactNode } from "react";

/** Link to the player page (not for use inside another link). */
export function PlayerLink({ id, children, className = "" }: { id: number; children: ReactNode; className?: string }) {
  return (
    <Link href={`/spieler/${id}`} className={`hover:underline hover:decoration-slate-300 hover:underline-offset-4 ${className}`}>
      {children}
    </Link>
  );
}
