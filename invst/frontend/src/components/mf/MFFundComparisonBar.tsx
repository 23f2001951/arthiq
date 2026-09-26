import React from 'react';
import { Award, ArrowUpRight } from 'lucide-react';

interface MFFundComparisonBarProps {
  fundName: string;
  category: string;
  benchmarkName?: string;
  trailingReturns: Record<string, number | null>;
  expenseRatio?: number;
}

export const MFFundComparisonBar: React.FC<MFFundComparisonBarProps> = ({
  fundName,
  category,
  benchmarkName = 'Category Benchmark',
  trailingReturns,
  expenseRatio,
}) => {
  // Approximate benchmark trailing returns based on category
  const getBenchmarkReturn = (period: string) => {
    const isMidOrSmall = category.includes('Mid') || category.includes('Small');
    const isDebt = category.includes('Debt') || category.includes('Liquid');
    const isHybrid = category.includes('Hybrid') || category.includes('Balanced');

    if (isDebt) {
      if (period === '1y') return 0.072;
      if (period === '3y') return 0.068;
      if (period === '5y') return 0.065;
      return 0.07;
    }
    if (isHybrid) {
      if (period === '1y') return 0.165;
      if (period === '3y') return 0.142;
      if (period === '5y') return 0.138;
      return 0.14;
    }
    if (isMidOrSmall) {
      if (period === '1y') return 0.285;
      if (period === '3y') return 0.224;
      if (period === '5y') return 0.210;
      return 0.22;
    }
    // Large / Flexi cap defaults
    if (period === '1y') return 0.228;
    if (period === '3y') return 0.168;
    if (period === '5y') return 0.155;
    return 0.17;
  };

  const periods = ['1y', '3y', '5y'].filter((p) => trailingReturns[p] !== undefined && trailingReturns[p] !== null);

  return (
    <div className="bg-slate-900/70 rounded-2xl border border-slate-800/80 p-5 space-y-4 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/70 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Award className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              Fund vs. Benchmark Alpha Comparison
            </h3>
            <p className="text-[11px] text-slate-400 truncate max-w-sm">
              {fundName} vs {benchmarkName}
            </p>
          </div>
        </div>
        {expenseRatio !== undefined && (
          <span className="text-[10px] text-slate-300 font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
            TER: <strong className="text-emerald-400">{expenseRatio}%</strong>
          </span>
        )}
      </div>

      <div className="space-y-4">
        {periods.map((p) => {
          const fundVal = (trailingReturns[p] ?? 0) * 100;
          const benchVal = getBenchmarkReturn(p) * 100;
          const alphaSpread = fundVal - benchVal;
          const maxVal = Math.max(fundVal, benchVal, 30);

          const fundWidth = Math.min(100, Math.max(5, (Math.abs(fundVal) / maxVal) * 100));
          const benchWidth = Math.min(100, Math.max(5, (Math.abs(benchVal) / maxVal) * 100));

          return (
            <div key={p} className="bg-slate-950/60 rounded-xl p-3 border border-slate-800/60 space-y-2.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-bold text-white uppercase tracking-wider">
                  {p.toUpperCase()} Horizon
                </span>
                <span
                  className={`text-[11px] font-bold px-2 py-0.5 rounded flex items-center gap-1 ${
                    alphaSpread >= 0
                      ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                      : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                  }`}
                >
                  <ArrowUpRight className="h-3 w-3" />
                  Alpha: {alphaSpread >= 0 ? '+' : ''}
                  {alphaSpread.toFixed(1)}%
                </span>
              </div>

              {/* Fund Bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-300 font-medium truncate max-w-[220px]">{fundName}</span>
                  <span className="font-bold font-mono text-emerald-400">{fundVal.toFixed(1)}%</span>
                </div>
                <div className="h-2.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-500"
                    style={{ width: `${fundWidth}%` }}
                  />
                </div>
              </div>

              {/* Benchmark Bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400 font-medium">{benchmarkName}</span>
                  <span className="font-bold font-mono text-slate-300">{benchVal.toFixed(1)}%</span>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-slate-600 transition-all duration-500"
                    style={{ width: `${benchWidth}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
