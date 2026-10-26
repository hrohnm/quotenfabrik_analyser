"use client";

import Image from "next/image";
import { useState } from "react";

type Props = {
  src?: string | null;
  alt: string;
  size?: number;
  /** "round" for player photos */
  shape?: "square" | "round";
  className?: string;
};

/** Logo / photo with a neutral fallback (initials) if the image is missing or cannot be loaded. */
export function Logo({ src, alt, size = 24, shape = "square", className = "" }: Props) {
  const [failed, setFailed] = useState(false);
  const rounded = shape === "round" ? "rounded-full" : "rounded";
  if (!src || failed) {
    const initials = alt.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
    return (
      <span
        aria-label={alt}
        className={`inline-grid shrink-0 place-items-center bg-slate-200 font-semibold text-slate-500 ${rounded} ${className}`}
        style={{ width: size, height: size, fontSize: Math.max(8, size * 0.36) }}
      >
        {initials}
      </span>
    );
  }
  return (
    <Image
      src={src}
      alt={alt}
      width={size}
      height={size}
      onError={() => setFailed(true)}
      unoptimized={src.endsWith(".svg")}
      className={`shrink-0 object-contain ${shape === "round" ? "rounded-full bg-slate-100 object-cover" : ""} ${className}`}
      style={{ width: size, height: size }}
    />
  );
}
