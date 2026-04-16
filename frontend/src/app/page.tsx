import { Activity, BarChart3, Newspaper, TrendingUp } from "lucide-react";

const pairs = ["EUR/USD", "USD/JPY", "EUR/JPY"];

function PairCard({ pair }: { pair: string }) {
  return (
    <div className="rounded-2xl bg-bg-card border border-primary-800/30 p-6 hover:border-primary-500/50 transition-all">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">{pair}</h3>
        <span className="text-xs px-2 py-1 rounded-full bg-primary-900/50 text-primary-300">
          รอข้อมูล
        </span>
      </div>
      <div className="text-3xl font-bold text-accent-400">—</div>
      <p className="text-sm text-text-secondary mt-2">ราคาจะแสดงใน Phase 3</p>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-bg-surface p-4">
      <div className="p-2 rounded-lg bg-primary-600/20">
        <Icon className="w-5 h-5 text-primary-400" />
      </div>
      <div>
        <p className="text-sm text-text-secondary">{label}</p>
        <p className="text-lg font-semibold">{value}</p>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <main className="min-h-screen p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-bold text-xl">
          S
        </div>
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-primary-400 to-accent-400 bg-clip-text text-transparent">
            Sochron1k
          </h1>
          <p className="text-sm text-text-secondary">
            ระบบวิเคราะห์ Forex อัจฉริยะ
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard icon={TrendingUp} label="สัญญาณวันนี้" value="—" />
        <StatCard icon={Activity} label="Win Rate" value="—" />
        <StatCard icon={Newspaper} label="ข่าวล่าสุด" value="—" />
        <StatCard icon={BarChart3} label="เทรดทั้งหมด" value="0" />
      </div>

      {/* Pair Cards */}
      <h2 className="text-lg font-semibold mb-4 text-text-secondary">
        คู่สกุลเงินที่ติดตาม
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {pairs.map((pair) => (
          <PairCard key={pair} pair={pair} />
        ))}
      </div>

      {/* Status */}
      <div className="rounded-2xl bg-bg-card border border-primary-800/30 p-6">
        <h2 className="text-lg font-semibold mb-3">สถานะระบบ</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">API Backend</span>
            <span className="text-success">● ออนไลน์</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">ฐานข้อมูล</span>
            <span className="text-warning">● รอเชื่อมต่อ</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Web Scraper</span>
            <span className="text-text-muted">● Phase 2</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">AI Engine</span>
            <span className="text-text-muted">● Phase 2</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Indicators</span>
            <span className="text-text-muted">● Phase 3</span>
          </div>
        </div>
      </div>
    </main>
  );
}
