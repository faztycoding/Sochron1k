"use client";

import { useEffect, useRef } from "react";
import type { CandleData } from "@/lib/api";

interface OscillatorPaneProps {
  candles: CandleData[];
  rsi?: (number | null)[];
  macdLine?: (number | null)[];
  macdSignal?: (number | null)[];
  macdHist?: (number | null)[];
  type: "rsi" | "macd";
  height?: number;
}

export function OscillatorPane({
  candles,
  rsi,
  macdLine,
  macdSignal,
  macdHist,
  type,
  height = 140,
}: OscillatorPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof import("lightweight-charts").createChart> | null>(null);

  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;
    let disposed = false;

    (async () => {
      const { createChart, LineStyle } = await import("lightweight-charts");
      if (disposed || !containerRef.current) return;
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
          fontSize: 10,
        },
        grid: {
          vertLines: { color: "#1a1333" },
          horzLines: { color: "#1a1333" },
        },
        timeScale: { borderColor: "#2e2650", timeVisible: true },
        rightPriceScale: { borderColor: "#2e2650" },
        crosshair: {
          vertLine: { color: "#7c3aed", width: 1, style: 2 },
          horzLine: { color: "#7c3aed", width: 1, style: 2 },
        },
      });
      chartRef.current = chart;

      const sorted = [...candles].sort((a, b) => a.open_time.localeCompare(b.open_time));

      const toPoints = (arr: (number | null)[] | undefined) => {
        if (!arr) return [];
        const out: { time: import("lightweight-charts").UTCTimestamp; value: number }[] = [];
        const limit = Math.min(arr.length, sorted.length);
        for (let i = 0; i < limit; i++) {
          const v = arr[i];
          if (v == null || Number.isNaN(v)) continue;
          out.push({
            time: (new Date(sorted[i].open_time).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
            value: v,
          });
        }
        return out;
      };

      if (type === "rsi") {
        const rsiPoints = toPoints(rsi);
        if (rsiPoints.length) {
          const rsiSeries = chart.addLineSeries({
            color: "#8b5cf6",
            lineWidth: 2,
            priceFormat: { type: "price", precision: 1, minMove: 0.1 },
          });
          rsiSeries.setData(rsiPoints);

          // Reference lines at 30/50/70
          rsiSeries.createPriceLine({
            price: 70,
            color: "rgba(239, 68, 68, 0.5)",
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: "OB",
          });
          rsiSeries.createPriceLine({
            price: 50,
            color: "rgba(148, 163, 184, 0.3)",
            lineWidth: 1,
            lineStyle: LineStyle.Dotted,
            axisLabelVisible: false,
            title: "",
          });
          rsiSeries.createPriceLine({
            price: 30,
            color: "rgba(34, 197, 94, 0.5)",
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: "OS",
          });
        }
      }

      if (type === "macd") {
        const histPoints = toPoints(macdHist).map((p) => ({
          time: p.time,
          value: p.value,
          color: p.value >= 0 ? "rgba(34, 197, 94, 0.6)" : "rgba(239, 68, 68, 0.6)",
        }));
        if (histPoints.length) {
          const histSeries = chart.addHistogramSeries({
            priceFormat: { type: "price", precision: 6, minMove: 0.000001 },
          });
          histSeries.setData(histPoints);
        }

        const linePoints = toPoints(macdLine);
        if (linePoints.length) {
          const line = chart.addLineSeries({
            color: "#60a5fa",
            lineWidth: 2,
            priceLineVisible: false,
            priceFormat: { type: "price", precision: 6, minMove: 0.000001 },
          });
          line.setData(linePoints);
        }

        const signalPoints = toPoints(macdSignal);
        if (signalPoints.length) {
          const sig = chart.addLineSeries({
            color: "#f59e0b",
            lineWidth: 2,
            priceLineVisible: false,
            priceFormat: { type: "price", precision: 6, minMove: 0.000001 },
          });
          sig.setData(signalPoints);
        }
      }

      chart.timeScale().fitContent();

      const observer = new ResizeObserver((entries) => {
        for (const entry of entries) chart.applyOptions({ width: entry.contentRect.width });
      });
      observer.observe(containerRef.current);

      return () => observer.disconnect();
    })();

    return () => {
      disposed = true;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [candles, rsi, macdLine, macdSignal, macdHist, type, height]);

  const label = type === "rsi" ? "RSI (14)" : "MACD (12,26,9)";

  return (
    <div className="relative rounded-xl overflow-hidden border border-border bg-bg-dark">
      <div className="absolute top-2 left-3 z-10 text-[10px] font-medium text-text-muted">
        {label}
      </div>
      <div ref={containerRef} style={{ height }} />
    </div>
  );
}
