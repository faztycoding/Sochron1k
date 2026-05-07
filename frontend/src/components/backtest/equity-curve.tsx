"use client";

import { useEffect, useRef } from "react";

interface EquityCurveProps {
  data: { time: string; equity: number }[];
  initialBalance: number;
  height?: number;
}

export function EquityCurve({ data, initialBalance, height = 260 }: EquityCurveProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof import("lightweight-charts").createChart> | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;
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
        },
        grid: {
          vertLines: { color: "#1a1333" },
          horzLines: { color: "#1a1333" },
        },
        crosshair: {
          vertLine: { color: "#7c3aed", width: 1, style: 2, labelBackgroundColor: "#7c3aed" },
          horzLine: { color: "#7c3aed", width: 1, style: 2, labelBackgroundColor: "#7c3aed" },
        },
        timeScale: { borderColor: "#2e2650", timeVisible: true },
        rightPriceScale: { borderColor: "#2e2650" },
      });
      chartRef.current = chart;

      const series = chart.addAreaSeries({
        lineColor: "#8b5cf6",
        topColor: "rgba(139, 92, 246, 0.4)",
        bottomColor: "rgba(139, 92, 246, 0.02)",
        lineWidth: 2,
        priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      });

      series.setData(
        data
          .map((d) => ({
            time: (new Date(d.time).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
            value: d.equity,
          }))
          .sort((a, b) => (a.time as number) - (b.time as number)),
      );

      // Baseline — initial balance
      series.createPriceLine({
        price: initialBalance,
        color: "#475569",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "start",
      });

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
  }, [data, initialBalance, height]);

  return (
    <div className="relative rounded-xl overflow-hidden border border-border bg-bg-dark">
      <div ref={containerRef} style={{ height }} />
      {data.length === 0 && (
        <div
          className="absolute inset-0 flex items-center justify-center text-text-muted text-sm"
          style={{ height }}
        >
          ยังไม่ได้รัน backtest
        </div>
      )}
    </div>
  );
}
