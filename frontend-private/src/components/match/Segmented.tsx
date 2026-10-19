"use client";

type Option = { key: string; label: string };

export function Segmented({ options, value, onChange, size = "md" }: { options: Option[]; value: string; onChange: (v: string) => void; size?: "sm" | "md" }) {
  const pad = size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm";
  return (
    <div className="inline-flex max-w-full overflow-x-auto rounded-lg bg-slate-100 p-1">
      {options.map((o) => (
        <button
          key={o.key}
          type="button"
          onClick={() => onChange(o.key)}
          className={`whitespace-nowrap rounded-md ${pad} transition ${value === o.key ? "bg-white font-medium text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
