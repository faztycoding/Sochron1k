import { useEffect, useRef, useState } from "react";
import type { IChartApi, ISeriesApi, UTCTimestamp, CandlestickData, WhitespaceData, Time } from "lightweight-charts";
import { periods, type ChartObservation } from "./chart-api";

export function candlePoints(observation: ChartObservation): Array<CandlestickData<UTCTimestamp> | WhitespaceData<UTCTimestamp>> {
  const points: Array<CandlestickData<UTCTimestamp> | WhitespaceData<UTCTimestamp>> = [];
  let previous = 0;
  for (const bar of observation.bars) {
    const time = Date.parse(bar.open_time_utc) / 1000;
    // One whitespace slot marks any gap. Exact gap lengths are shown outside canvas.
    if (previous && time - previous > periods[observation.timeframe]) points.push({ time: (previous + periods[observation.timeframe]) as UTCTimestamp });
    points.push({ time: time as UTCTimestamp, open: Number(bar.open), high: Number(bar.high), low: Number(bar.low), close: Number(bar.close),
      ...(!bar.closed ? { color: "#d6b46a", borderColor: "#d6b46a", wickColor: "#d6b46a" } : {}) });
    previous = time;
  }
  return points;
}

export function CandleCanvas({ observation }: { observation: ChartObservation }) {
  const element = useRef<HTMLDivElement>(null);
  const fitted = useRef(false);
  const [instance, setInstance] = useState<{ chart: IChartApi; series: ISeriesApi<"Candlestick"> } | null>(null);
  const [failed, setFailed] = useState(false);
  const { digits, tick_size: tickSize } = observation;
  useEffect(() => {
    let disposed = false;
    let chart: IChartApi | undefined;
    fitted.current = false;
    setFailed(false);
    void import("lightweight-charts").then(({ createChart, CandlestickSeries, ColorType }) => {
      if (disposed || !element.current) return;
      chart = createChart(element.current, {
        autoSize: true,
        layout: { background: { type: ColorType.Solid, color: "#11171e" }, textColor: "#98a2b3", fontFamily: "Inter, sans-serif", attributionLogo: true },
        grid: { vertLines: { color: "#202934" }, horzLines: { color: "#202934" } },
        rightPriceScale: { borderColor: "#303946" },
        timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#303946" },
        localization: { locale: "en-GB", timeFormatter: (time: Time) => typeof time === "number" ? new Date(time * 1000).toISOString().replace("T", " ").slice(0, 16) + " UTC" : String(time) },
      });
      const series = chart.addSeries(CandlestickSeries, {
        upColor: "#39c98a", downColor: "#f0646b", wickUpColor: "#39c98a", wickDownColor: "#f0646b", borderVisible: false,
        priceFormat: { type: "price", precision: digits, minMove: Number(tickSize) },
        lastValueVisible: false, priceLineVisible: false,
      });
      setInstance({ chart, series });
    }).catch(() => { if (!disposed) setFailed(true); });
    return () => { disposed = true; chart?.remove(); };
  }, [digits, tickSize]);
  useEffect(() => {
    if (!instance) return;
    try {
      instance.series.setData(candlePoints(observation));
      if (!fitted.current) { instance.chart.timeScale().fitContent(); fitted.current = true; }
    } catch { setFailed(true); }
  }, [instance, observation]);
  return <>
    <div ref={element} className="candle-canvas" role="img" aria-label={`กราฟแท่งเทียน ${observation.timeframe} เวลา UTC; ค่า OHLC แบบข้อความอยู่ด้านล่าง`} />
    {failed ? <p role="alert">แสดงกราฟไม่ได้ อ่านค่าที่ตรวจสอบแล้วในตารางด้านล่าง หรือโหลดหน้าใหม่</p> : null}
  </>;
}
