"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  duration?: number;
  className?: string;
  flashOnChange?: boolean;
  prefix?: string;
  suffix?: string;
}

/**
 * Smoothly animates number changes with easing + flash background on update.
 */
export function AnimatedNumber({
  value,
  decimals = 0,
  duration = 600,
  className,
  flashOnChange = true,
  prefix = "",
  suffix = "",
}: AnimatedNumberProps) {
  const [display, setDisplay] = useState(value);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const prevRef = useRef(value);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const from = prevRef.current;
    const to = value;

    if (from === to) return;

    if (flashOnChange) {
      setFlash(to > from ? "up" : "down");
      const t = setTimeout(() => setFlash(null), 600);
      // cleanup via return handles timeout
      const start = performance.now();
      const animate = (now: number) => {
        const elapsed = now - start;
        const progress = Math.min(1, elapsed / duration);
        // easeOutCubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = from + (to - from) * eased;
        setDisplay(current);
        if (progress < 1) {
          rafRef.current = requestAnimationFrame(animate);
        } else {
          setDisplay(to);
          prevRef.current = to;
        }
      };
      rafRef.current = requestAnimationFrame(animate);

      return () => {
        clearTimeout(t);
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
      };
    }

    prevRef.current = to;
    setDisplay(to);
  }, [value, duration, flashOnChange]);

  return (
    <span
      className={cn(
        "tabular-nums transition-colors duration-300 inline-block",
        flash === "up" && "text-emerald-400",
        flash === "down" && "text-red-400",
        className
      )}
    >
      {prefix}
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}
