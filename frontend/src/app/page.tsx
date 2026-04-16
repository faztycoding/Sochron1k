"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, BarChart3, BookOpen, Calculator, Newspaper, Trophy, TrendingUp, ChevronRight } from "lucide-react";
import Link from "next/link";

import { api } from "@/lib/api";
import type { PriceData, AnalysisResult, NewsItem, CurrencyStrength, SessionInfo } from "@/lib/api";

import { PriceCard } from "@/components/dashboard/price-card";
import { NewsFeed } from "@/components/dashboard/news-feed";
import { SignalPanel } from "@/components/dashboard/signal-panel";
import { CurrencyStrengthBar } from "@/components/dashboard/currency-strength";
import { SessionInfoBar } from "@/components/dashboard/session-info";

const PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY"];

function StatCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-bg-surface p-4">
      <div className="p-2 rounded-lg bg-primary-600/20">
        <Icon className="w-5 h-5 text-primary-400" />
      </div>
      <div>
        <p className="text-xs text-text-muted">{label}</p>
        <p className="text-lg font-semibold">{value}</p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [prices, setPrices] = useState<Record<string, PriceData>>({});
  const [analyses, setAnalyses] = useState<Record<string, AnalysisResult | null>>({});
  const [news, setNews] = useState<NewsItem[]>([]);
  const [strength, setStrength] = useState<CurrencyStrength | null>(null);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [newsLoading, setNewsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoadError(null);
      const [priceRes, sessionRes] = await Promise.allSettled([
        api.prices.realtime(),
        api.analysis.session(),
      ]);

      if (priceRes.status === "fulfilled") setPrices(priceRes.value.prices);
      if (sessionRes.status === "fulfilled") setSession(sessionRes.value);

      const [newsRes, strengthRes] = await Promise.allSettled([
        api.news.list(10),
        api.indicators.strength(),
      ]);

      if (newsRes.status === "fulfilled") setNews(newsRes.value.items || []);
      if (strengthRes.status === "fulfilled") setStrength(strengthRes.value);

      // Analysis — heavier, run after quick data
      const analysisRes = await Promise.allSettled(
        PAIRS.map((p) => api.analysis.run(p))
      );
      const newAnalyses: Record<string, AnalysisResult | null> = {};
      PAIRS.forEach((pair, i) => {
        newAnalyses[pair] = analysisRes[i].status === "fulfilled" ? analysisRes[i].value : null;
      });
      setAnalyses(newAnalyses);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "โหลดข้อมูลล้มเหลว");
    }
  }, []);

  const refreshNews = async () => {
    setNewsLoading(true);
    try {
      await api.news.refresh();
      const res = await api.news.list(10);
      setNews(res.items || []);
    } catch {
      // silent
    }
    setNewsLoading(false);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 60_000);
    return () => clearInterval(interval);
  }, [loadData]);

  const signalCount = Object.values(analyses).filter(
    (a) => a && a.direction !== "NO_TRADE" && a.confidence >= 0.5
  ).length;

  return (
    <main className="min-h-screen p-4 sm:p-6 max-w-7xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-bold text-lg sm:text-xl">
            S
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold gradient-text">Sochron1k</h1>
            <p className="text-xs sm:text-sm text-text-secondary">ระบบวิเคราะห์ Forex อัจฉริยะ</p>
          </div>
        </div>
        <nav className="flex items-center gap-1 sm:gap-2">
          {[
            { href: "/analysis", icon: TrendingUp, label: "วิเคราะห์" },
            { href: "/calculator", icon: Calculator, label: "คำนวณ" },
            { href: "/journal", icon: BookOpen, label: "บันทึก" },
            { href: "/stats", icon: Trophy, label: "สถิติ" },
          ].map((nav) => (
            <Link
              key={nav.href}
              href={nav.href}
              className="flex items-center gap-1 px-2 sm:px-3 py-1.5 rounded-lg text-xs sm:text-sm text-text-secondary hover:text-primary-400 hover:bg-bg-surface transition-all"
            >
              <nav.icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{nav.label}</span>
            </Link>
          ))}
        </nav>
      </div>

      {/* Session */}
      <div className="mb-5">
        <SessionInfoBar session={session} />
      </div>

      {loadError && (
        <div className="mb-4 p-3 rounded-xl bg-danger-dim/20 border border-danger/30 text-sm text-danger">
          {loadError} — ข้อมูลจะอัพเดทอัตโนมัติ
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatCard icon={TrendingUp} label="สัญญาณวันนี้" value={String(signalCount)} />
        <StatCard icon={Activity} label="Win Rate" value="—" />
        <StatCard icon={Newspaper} label="ข่าวล่าสุด" value={String(news.length)} />
        <StatCard icon={BarChart3} label="เทรดทั้งหมด" value="0" />
      </div>

      {/* Price Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        {PAIRS.map((pair) => (
          <PriceCard
            key={pair}
            pair={pair}
            price={prices[pair]}
            analysis={analyses[pair]}
          />
        ))}
      </div>

      {/* Bottom grid: Signals + News + Strength */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1">
          <SignalPanel analyses={analyses} />
        </div>
        <div className="lg:col-span-1">
          <NewsFeed items={news} onRefresh={refreshNews} loading={newsLoading} />
        </div>
        <div className="lg:col-span-1">
          <CurrencyStrengthBar data={strength} />
        </div>
      </div>
    </main>
  );
}
