"use client";

import { useEffect } from "react";

/** Scrolls the element with the given id into the visible part of its scroll container. */
export function ScrollToActive({ id }: { id: string }) {
  useEffect(() => {
    document.getElementById(id)?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [id]);
  return null;
}
