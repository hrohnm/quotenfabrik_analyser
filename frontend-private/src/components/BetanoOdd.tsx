import { odd, pct, signedPct } from "@/lib/format";
import type { BookPrices } from "@/lib/types";

/** Edge from which a Betano price counts as value (model probability × odds − 1). */
export const VALUE_EDGE = 0.05;

export const isValue = (p: BookPrices) => p.edge != null && p.edge >= VALUE_EDGE;

/** Betano odds as a small chip; green when the model sees value. Tooltip: Pinnacle without margin and edge. */
export function BetanoOdd({ prices, className = "" }: { prices: BookPrices; className?: string }) {
  if (prices.betano == null) return null;
  const title = [
    `Betano ${odd(prices.betano)}`,
    prices.pinnacle != null ? `Pinnacle ohne Marge ${pct(prices.pinnacle)}` : null,
    prices.edge != null ? `Vorteil laut Modell ${signedPct(prices.edge)}` : null,
  ].filter(Boolean).join(" · ");
  return (
    <span
      title={title}
      className={`inline-flex items-center rounded px-1 text-xs font-medium tabular-nums ${isValue(prices) ? "bg-emerald-100 text-emerald-800" : "bg-orange-50 text-orange-700"} ${className}`}
    >
      {odd(prices.betano)}
    </span>
  );
}
