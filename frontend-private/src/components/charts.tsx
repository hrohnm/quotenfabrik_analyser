"use client";

import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { pct } from "@/lib/format";

// Categorical slots 1 and 2 of the validated reference palette (blue / orange).
export const SERIES = { observed: "#2a78d6", expected: "#eb6834" };
const GRID = "#e5e7eb";
const AXIS = { fontSize: 11, fill: "#64748b" };

const pctTick = (v: number) => `${Math.round(v * 100)} %`;
const tooltipFmt = (v: number, name: string) => [pct(v), name];

/** Hit rate vs. expected hit rate per category (e.g. confidence bin or season). */
export function HitRateBars({ data, xKey, height = 260 }: { data: Record<string, number | string>[]; xKey: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} barGap={2} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey={xKey} tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} />
        <YAxis tickFormatter={pctTick} tick={AXIS} tickLine={false} axisLine={false} domain={[0, 1]} width={52} />
        <Tooltip formatter={tooltipFmt} cursor={{ fill: "#f1f5f9" }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="hit_rate" name="Getroffen" fill={SERIES.observed} radius={[4, 4, 0, 0]} maxBarSize={28} />
        <Bar dataKey="expected_hit_rate" name="Erwartet (Ø Wahrscheinlichkeit)" fill={SERIES.expected} radius={[4, 4, 0, 0]} maxBarSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Calibration: predicted vs. observed frequency; the diagonal is perfect calibration. */
export function CalibrationChart({ data, height = 260 }: { data: { bin: string; predicted: number; observed: number; n: number }[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="bin" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} />
        <YAxis tickFormatter={pctTick} tick={AXIS} tickLine={false} axisLine={false} domain={[0, 1]} width={52} />
        <Tooltip formatter={tooltipFmt} labelFormatter={(l, p) => `${l} · n = ${p?.[0]?.payload?.n ?? "–"}`} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="observed" name="Eingetreten" stroke={SERIES.observed} strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="predicted" name="Vorhergesagt" stroke={SERIES.expected} strokeWidth={2} strokeDasharray="4 3" dot={{ r: 4 }} />
        <ReferenceLine y={0} stroke={GRID} />
      </LineChart>
    </ResponsiveContainer>
  );
}
