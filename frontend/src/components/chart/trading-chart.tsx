"use client";

import { useEffect, useRef, useState } from "react";
import type { CandleData } from "@/lib/api";

export interface IndicatorSeriesData {
  candles?: CandleData[];
  ema_9?: (number | null)[];
  ema_21?: (number | null)[];
  ema_50?: (number | null)[];
  ema_200?: (number | null)[];
  bb_upper?: (number | null)[];
  bb_middle?: (number | null)[];
  bb_lower?: (number | null)[];
}

export interface IndicatorToggles {
  ema?: boolean;   // shows EMA 9/21/50
  bb?: boolean;    // shows Bollinger Bands
}

interface TradingChartProps {
  candles: CandleData[];
  pair: string;
  /** optional per-candle indicator series aligned to `candles` */
  series?: IndicatorSeriesData | null;
  toggles?: IndicatorToggles;
  height?: number;
}

export function TradingChart({
  candles,
  pair,
  series,
  toggles,
  height = 400,
}: TradingChartProps) {
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

      // ───────── Indicator overlays ─────────
      // `series` has arrays aligned to `candles` (both sorted oldest→newest).
      // We build overlay points by zipping values with candle timestamps.
      const withSeries = (arr: (number | null)[] | undefined) => {
        if (!arr || arr.length === 0) return [];
        const out: { time: import("lightweight-charts").UTCTimestamp; value: number }[] = [];
        const sortedCandles = [...candles].sort((a, b) => a.open_time.localeCompare(b.open_time));
        const limit = Math.min(arr.length, sortedCandles.length);
        for (let i = 0; i < limit; i++) {
          const v = arr[i];
          if (v == null || Number.isNaN(v)) continue;
          out.push({
            time: (new Date(sortedCandles[i].open_time).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
            value: v,
          });
        }
        return out;
      };

      if (series && toggles?.ema) {
        const emaSpecs: { data?: (number | null)[]; color: string; title: string; width: 1 | 2 | 3 | 4 }[] = [
          { data: series.ema_9, color: "#22d3ee", title: "EMA 9", width: 2 },
          { data: series.ema_21, color: "#f59e0b", title: "EMA 21", width: 2 },
          { data: series.ema_50, color: "#a855f7", title: "EMA 50", width: 2 },
        ];
        for (const spec of emaSpecs) {
          const data = withSeries(spec.data);
          if (data.length === 0) continue;
          const line = chart.addLineSeries({
            color: spec.color,
            lineWidth: spec.width,
            priceLineVisible: false,
            lastValueVisible: true,
            title: spec.title,
          });
          line.setData(data);
        }
      }

      if (series && toggles?.bb) {
        const bbUpper = withSeries(series.bb_upper);
        const bbMid = withSeries(series.bb_middle);
        const bbLower = withSeries(series.bb_lower);
        if (bbUpper.length) {
          const upper = chart.addLineSeries({
            color: "rgba(148, 163, 184, 0.7)",
            lineWidth: 1,
            lineStyle: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            title: "BB Upper",
          });
          upper.setData(bbUpper);
        }
        if (bbMid.length) {
          const mid = chart.addLineSeries({
            color: "rgba(148, 163, 184, 0.5)",
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
            title: "BB Mid",
          });
          mid.setData(bbMid);
        }
        if (bbLower.length) {
          const lower = chart.addLineSeries({
            color: "rgba(148, 163, 184, 0.7)",
            lineWidth: 1,
            lineStyle: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            title: "BB Lower",
          });
          lower.setData(bbLower);
        }
      }

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
  }, [candles, height, series, toggles?.ema, toggles?.bb]);

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
