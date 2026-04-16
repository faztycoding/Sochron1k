"use client";

import { useEffect, useRef, useState } from "react";
import type { CandleData } from "@/lib/api";

interface TradingChartProps {
  candles: CandleData[];
  pair: string;
  emaData?: { ema_9?: number; ema_21?: number; ema_50?: number };
  bbData?: { bb_upper?: number; bb_middle?: number; bb_lower?: number };
  height?: number;
}

export function TradingChart({ candles, pair, emaData, bbData, height = 400 }: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof import("lightweight-charts").createChart> | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    let disposed = false;

    (async () => {
      const { createChart } = await import("lightweight-charts");
      if (disposed || !containerRef.current) return;

      // Dispose previous chart
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }

      const chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height,
        layout: {
          background: { color: "#0f0b1a" },
          textColor: "#a5a0b8",
          fontFamily: "Inter, Noto Sans Thai, sans-serif",
        },
        grid: {
          vertLines: { color: "#1a1333" },
          horzLines: { color: "#1a1333" },
        },
        crosshair: {
          vertLine: { color: "#7c3aed", width: 1, style: 2, labelBackgroundColor: "#7c3aed" },
          horzLine: { color: "#7c3aed", width: 1, style: 2, labelBackgroundColor: "#7c3aed" },
        },
        timeScale: {
          borderColor: "#2e2650",
          timeVisible: true,
        },
        rightPriceScale: {
          borderColor: "#2e2650",
        },
      });

      chartRef.current = chart;

      // Candlestick
      const candleSeries = chart.addCandlestickSeries({
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderUpColor: "#22c55e",
        borderDownColor: "#ef4444",
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      });

      const candleChartData = candles
        .map((c) => ({
          time: (new Date(c.open_time).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }))
        .sort((a, b) => (a.time as number) - (b.time as number));

      candleSeries.setData(candleChartData);

      // Volume
      const volumeSeries = chart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });

      chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.85, bottom: 0 },
      });

      volumeSeries.setData(
        candles
          .map((c) => ({
            time: (new Date(c.open_time).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
            value: c.volume,
            color: c.close >= c.open ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)",
          }))
          .sort((a, b) => (a.time as number) - (b.time as number))
      );

      chart.timeScale().fitContent();

      // Resize
      const observer = new ResizeObserver((entries) => {
        for (const entry of entries) {
          chart.applyOptions({ width: entry.contentRect.width });
        }
      });
      observer.observe(containerRef.current);

      setLoaded(true);

      return () => {
        observer.disconnect();
      };
    })();

    return () => {
      disposed = true;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [candles, height]);

  return (
    <div className="relative rounded-xl overflow-hidden border border-border bg-bg-dark">
      <div ref={containerRef} style={{ height }} />
      {!loaded && candles.length > 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-text-muted text-sm">
          กำลังโหลดชาร์ท...
        </div>
      )}
      {candles.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-text-muted text-sm" style={{ height }}>
          ไม่มีข้อมูลแท่งเทียน
        </div>
      )}
    </div>
  );
}
