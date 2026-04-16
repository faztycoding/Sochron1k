"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Trophy, Target, TrendingUp, BarChart3 } from "lucide-react";

import { tradeApi } from "@/lib/api-trade";
import type { WinRateStats, OverviewStats } from "@/lib/api-trade";
import { Card, CardHeader, CardTitle, CardValue } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function MetricCard({ icon: Icon, label, value, sub, color }: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-text-muted mb-1">{label}</p>
          <CardValue className={color || ""}>{value}</CardValue>
          {sub && <p className="text-xs text-text-muted mt-1">{sub}</p>}
        </div>
        <div className="p-2 rounded-lg bg-primary-600/15">
          <Icon className="w-4 h-4 text-primary-400" />
        </div>
      </div>
    </Card>
  );
}

export default function StatsPage() {
  const [winrate, setWinrate] = useState<WinRateStats | null>(null);
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [accuracy, setAccuracy] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [wr, ov, acc] = await Promise.allSettled([
        tradeApi.stats.winrate(),
        tradeApi.stats.overview(),
        tradeApi.stats.accuracy(),
      ]);
      if (wr.status === "fulfilled") setWinrate(wr.value);
      if (ov.status === "fulfilled") setOverview(ov.value);
      if (acc.status === "fulfilled") setAccuracy(acc.value);
    } catch {
      // silent
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <main className="min-h-screen p-4 sm:p-6 max-w-6xl mx-auto">
        <p className="text-text-muted text-center py-20">กำลังโหลดสถิติ...</p>
      </main>
    );
  }

  const wr = winrate;
  const ov = overview;

  return (
    <main className="min-h-screen p-4 sm:p-6 max-w-6xl mx-auto animate-fade-in">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="p-2 rounded-lg hover:bg-bg-surface transition-colors">
          <ArrowLeft className="w-5 h-5 text-text-muted" />
        </Link>
        <Trophy className="w-5 h-5 text-warning" />
        <h1 className="text-xl font-bold gradient-text">สถิติ & Win Rate</h1>
      </div>

      {/* Overview metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <MetricCard
          icon={TrendingUp}
          label="Win Rate"
          value={`${ov?.win_rate ?? 0}%`}
          sub={`${wr?.wins ?? 0}W / ${wr?.losses ?? 0}L`}
          color={ov && ov.win_rate >= 60 ? "text-buy" : ov && ov.win_rate >= 50 ? "text-warning" : "text-sell"}
        />
        <MetricCard
          icon={BarChart3}
          label="Total Pips"
          value={`${ov?.total_pips ?? 0}`}
          sub={`วันนี้: ${ov?.today_pips ?? 0} pips`}
          color={ov && ov.total_pips >= 0 ? "text-buy" : "text-sell"}
        />
        <MetricCard
          icon={Target}
          label="ความแม่นระบบ"
          value={`${ov?.system_accuracy ?? 0}%`}
          sub={`Avg conf: ${((ov?.avg_confidence ?? 0) * 100).toFixed(0)}%`}
        />
        <MetricCard
          icon={Trophy}
          label="Profit Factor"
          value={`${ov?.profit_factor ?? 0}`}
          sub={ov?.best_pair ? `Best: ${ov.best_pair}` : ""}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Win Rate by Pair */}
        <Card>
          <CardHeader>
            <CardTitle>Win Rate แยกคู่เงิน</CardTitle>
          </CardHeader>
          {wr && Object.keys(wr.by_pair).length > 0 ? (
            <div className="flex flex-col gap-3">
              {Object.entries(wr.by_pair).map(([pair, data]) => (
                <div key={pair}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{pair}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-text-muted">{data.wins}W/{data.losses}L</span>
                      <Badge variant={data.win_rate >= 60 ? "success" : data.win_rate >= 50 ? "warning" : "danger"}>
                        {data.win_rate}%
                      </Badge>
                    </div>
                  </div>
                  <div className="h-2 rounded-full bg-bg-surface overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${data.win_rate}%`,
                        background: data.win_rate >= 60
                          ? "linear-gradient(90deg, var(--color-primary-600), var(--color-buy))"
                          : data.win_rate >= 50
                            ? "linear-gradient(90deg, var(--color-warning-dim), var(--color-warning))"
                            : "linear-gradient(90deg, var(--color-danger-dim), var(--color-sell))",
                      }}
                    />
                  </div>
                  <div className="text-xs text-text-muted mt-1">
                    {data.total_pips > 0 ? "+" : ""}{data.total_pips} pips
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted text-center py-8">ยังไม่มีข้อมูล</p>
          )}
        </Card>

        {/* Detailed Stats */}
        <Card>
          <CardHeader>
            <CardTitle>สถิติโดยละเอียด</CardTitle>
          </CardHeader>
          {wr ? (
            <div className="flex flex-col gap-2 text-sm">
              {[
                ["เทรดทั้งหมด", String(wr.total_trades)],
                ["กำไรเฉลี่ย (pips)", `+${wr.avg_profit_pips}`],
                ["ขาดทุนเฉลี่ย (pips)", `-${wr.avg_loss_pips}`],
                ["เทรดดีที่สุด", `+${wr.best_trade_pips} pips`],
                ["เทรดแย่ที่สุด", `${wr.worst_trade_pips} pips`],
                ["ชนะติด", `${ov?.consecutive_wins ?? 0} ครั้ง`],
                ["แพ้ติด", `${ov?.consecutive_losses ?? 0} ครั้ง`],
                ["เทรดวันนี้", `${ov?.today_trades ?? 0}`],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between py-1.5 border-b border-border/30">
                  <span className="text-text-muted">{label}</span>
                  <span className="font-mono">{value}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted text-center py-8">ยังไม่มีข้อมูล</p>
          )}
        </Card>
      </div>

      {/* System Accuracy Detail */}
      {accuracy && (accuracy as Record<string, unknown>).total_signals !== undefined && (
        <Card>
          <CardHeader>
            <CardTitle>ความแม่นยำของระบบ AI</CardTitle>
            <Badge variant="default">
              {(accuracy as Record<string, unknown>).accuracy as number}% accuracy
            </Badge>
          </CardHeader>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {Object.entries((accuracy as Record<string, Record<string, unknown>>).by_confidence_tier || {}).map(([tier, data]) => (
              <div key={tier} className="p-3 rounded-xl bg-bg-surface/50">
                <p className="text-xs text-text-muted mb-1">{tier.replace("_", " ")}</p>
                <p className="text-lg font-mono font-semibold">{(data as Record<string, number>).accuracy ?? 0}%</p>
                <p className="text-xs text-text-muted">
                  {(data as Record<string, number>).correct ?? 0}/{(data as Record<string, number>).total ?? 0} ถูก
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </main>
  );
}
