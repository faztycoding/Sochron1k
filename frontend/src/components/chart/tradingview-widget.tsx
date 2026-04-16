"use client";

import { useEffect, useRef, memo } from "react";

interface TradingViewWidgetProps {
  pair: string;
  timeframe?: string;
  height?: number;
}

const SYMBOL_MAP: Record<string, string> = {
  "EUR/USD": "OANDA:EURUSD",
  "USD/JPY": "OANDA:USDJPY",
  "EUR/JPY": "OANDA:EURJPY",
  "GBP/USD": "OANDA:GBPUSD",
  "AUD/USD": "OANDA:AUDUSD",
};

const INTERVAL_MAP: Record<string, string> = {
  "1m": "1",
  "5m": "5",
  "15m": "15",
  "1h": "60",
  "4h": "240",
  "1d": "D",
  "1w": "W",
};

function TradingViewWidgetInner({ pair, timeframe = "1h", height = 500 }: TradingViewWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clear previous widget
    containerRef.current.innerHTML = "";

    const symbol = SYMBOL_MAP[pair] || "OANDA:EURUSD";
    const interval = INTERVAL_MAP[timeframe] || "60";

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol,
      interval,
      timezone: "Asia/Bangkok",
      theme: "dark",
      style: "1",
      locale: "th_TH",
      backgroundColor: "rgba(15, 11, 26, 1)",
      gridColor: "rgba(26, 19, 51, 0.6)",
      allow_symbol_change: true,
      calendar: false,
      support_host: "https://www.tradingview.com",
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: true,
      hide_volume: false,
      // Drawing tools
      drawings_access: {
        type: "all",
        tools: [{ name: "Regression Trend" }],
      },
      enabled_features: [
        "header_chart_type",
        "header_indicators",
        "header_compare",
        "header_undo_redo",
        "header_screenshot",
        "header_fullscreen_button",
        "drawing_templates",
      ],
      // Toolbar
      studies: [
        "RSI@tv-basicstudies",
        "MACD@tv-basicstudies",
        "BB@tv-basicstudies",
      ],
      // Colors
      overrides: {
        "mainSeriesProperties.candleStyle.upColor": "#22c55e",
        "mainSeriesProperties.candleStyle.downColor": "#ef4444",
        "mainSeriesProperties.candleStyle.borderUpColor": "#22c55e",
        "mainSeriesProperties.candleStyle.borderDownColor": "#ef4444",
        "mainSeriesProperties.candleStyle.wickUpColor": "#22c55e",
        "mainSeriesProperties.candleStyle.wickDownColor": "#ef4444",
      },
    });

    containerRef.current.appendChild(script);
    scriptRef.current = script;

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [pair, timeframe]);

  return (
    <div className="tradingview-widget-container rounded-xl overflow-hidden border border-border" style={{ height }}>
      <div ref={containerRef} style={{ height: "100%", width: "100%" }} />
    </div>
  );
}

export const TradingViewWidget = memo(TradingViewWidgetInner);
