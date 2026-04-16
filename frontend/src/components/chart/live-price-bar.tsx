"use client";

import { useEffect, useRef, useState } from "react";
import { Activity, Wifi, WifiOff } from "lucide-react";
import type { PriceData } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface LivePriceBarProps {
  pair: string;
  onPriceUpdate?: (price: number) => void;
}

export function LivePriceBar({ pair, onPriceUpdate }: LivePriceBarProps) {
  const [price, setPrice] = useState<PriceData | null>(null);
  const [prevPrice, setPrevPrice] = useState<number | null>(null);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const [connected, setConnected] = useState(false);
  const sseRef = useRef<EventSource | null>(null);
  const priceRef = useRef<PriceData | null>(null);

  useEffect(() => {
    const sse = new EventSource(`${API_BASE}/price/stream`);
    sseRef.current = sse;

    sse.onopen = () => setConnected(true);

    sse.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.prices && data.prices[pair]) {
          const newData = data.prices[pair] as PriceData;
          const old = priceRef.current;

          if (old && newData.price !== old.price) {
            setPrevPrice(old.price);
            setFlash(newData.price > old.price ? "up" : "down");
            setTimeout(() => setFlash(null), 400);
          }

          priceRef.current = newData;
          setPrice(newData);
          onPriceUpdate?.(newData.price);
        }
      } catch {
        // parse error
      }
    };

    sse.onerror = () => {
      setConnected(false);
      sse.close();
      // Reconnect after 2s
      setTimeout(() => {
        if (sseRef.current === sse) {
          sseRef.current = null;
        }
      }, 2000);
    };

    return () => {
      sse.close();
      sseRef.current = null;
    };
  }, [pair]); // eslint-disable-line react-hooks/exhaustive-deps

  const isJPY = pair.includes("JPY");
  const decimals = isJPY ? 3 : 5;
  const currentPrice = price?.price ?? 0;
  const diff = prevPrice ? currentPrice - prevPrice : 0;
  const pips = isJPY ? diff * 100 : diff * 10000;
  const spread = price?.spread;
  const bid = price?.bid;
  const ask = price?.ask;

  return (
    <div className="flex items-center gap-4 px-4 py-2.5 rounded-xl bg-bg-surface/80 backdrop-blur border border-border">
      {/* Live indicator */}
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2.5 w-2.5">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${connected ? "bg-emerald-400" : "bg-amber-400"} opacity-75`} />
          <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${connected ? "bg-emerald-500" : "bg-amber-500"}`} />
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
          {currentPrice > 0 ? currentPrice.toFixed(decimals) : "—"}
        </span>
        {diff !== 0 && (
          <span
            className={`text-xs font-mono ${
              diff > 0 ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {diff > 0 ? "+" : ""}{pips.toFixed(1)}p
          </span>
        )}
      </div>

      {/* Bid / Ask / Spread */}
      {bid && ask && (
        <div className="hidden sm:flex items-center gap-3 text-[11px] font-mono text-text-muted">
          <span>B {bid.toFixed(decimals)}</span>
          <span>A {ask.toFixed(decimals)}</span>
          {spread !== undefined && <span className="text-accent-400">{spread.toFixed(1)}p</span>}
        </div>
      )}

      {/* Connection status */}
      <div className="ml-auto flex items-center gap-1 text-xs text-text-muted">
        {connected ? (
          <Wifi className="w-3 h-3 text-emerald-400" />
        ) : (
          <WifiOff className="w-3 h-3 text-amber-400" />
        )}
        <span className="hidden sm:inline">{price?.source === "websocket" ? "WS" : "SSE"}</span>
      </div>
    </div>
  );
}
