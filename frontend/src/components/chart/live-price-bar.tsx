"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Activity } from "lucide-react";
import { api } from "@/lib/api";
import type { PriceData } from "@/lib/api";

interface LivePriceBarProps {
  pair: string;
  onPriceUpdate?: (price: number) => void;
}

export function LivePriceBar({ pair, onPriceUpdate }: LivePriceBarProps) {
  const [price, setPrice] = useState<PriceData | null>(null);
  const [prevPrice, setPrevPrice] = useState<number | null>(null);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchPrice = useCallback(async () => {
    try {
      const res = await api.prices.realtime();
      const data = res.prices[pair];
      if (data) {
        if (price && data.price !== price.price) {
          setPrevPrice(price.price);
          setFlash(data.price > price.price ? "up" : "down");
          setTimeout(() => setFlash(null), 600);
        }
        setPrice(data);
        onPriceUpdate?.(data.price);
      }
    } catch {
      // silent
    }
  }, [pair, price, onPriceUpdate]);

  useEffect(() => {
    fetchPrice();
    intervalRef.current = setInterval(fetchPrice, 3_000); // every 3s
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [pair]); // eslint-disable-line react-hooks/exhaustive-deps

  const isJPY = pair.includes("JPY");
  const decimals = isJPY ? 3 : 5;
  const currentPrice = price?.price ?? 0;
  const diff = prevPrice ? currentPrice - prevPrice : 0;
  const pips = isJPY ? diff * 100 : diff * 10000;

  return (
    <div className="flex items-center gap-4 px-4 py-2.5 rounded-xl bg-bg-surface/80 backdrop-blur border border-border">
      {/* Live indicator */}
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
        </span>
        <span className="text-xs text-text-muted font-medium uppercase tracking-wider">LIVE</span>
      </div>

      {/* Pair */}
      <span className="text-sm font-semibold text-text-primary">{pair}</span>

      {/* Price */}
      <div className="flex items-baseline gap-2">
        <span
          className={`text-xl font-mono font-bold tabular-nums transition-colors duration-300 ${
            flash === "up"
              ? "text-emerald-400"
              : flash === "down"
                ? "text-red-400"
                : "text-text-primary"
          }`}
        >
          {currentPrice.toFixed(decimals)}
        </span>
        {diff !== 0 && (
          <span
            className={`text-xs font-mono ${
              diff > 0 ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {diff > 0 ? "+" : ""}{pips.toFixed(1)} pips
          </span>
        )}
      </div>

      {/* Spread indicator */}
      <div className="ml-auto flex items-center gap-1 text-xs text-text-muted">
        <Activity className="w-3 h-3" />
        <span>3s</span>
      </div>
    </div>
  );
}
