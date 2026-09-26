import React from 'react';
import { RotateCcw, ShieldCheck, TrendingUp } from 'lucide-react';
import { MFRollingReturnsResponse } from '../../types/api';

interface MFRollingReturnsVisualizerProps {
  rollingReturns: MFRollingReturnsResponse;
  windowYears: number;
  onWindowChange?: (years: number) => void;
}

export const MFRollingReturnsVisualizer: React.FC<MFRollingReturnsVisualizerProps> = ({
  rollingReturns,
  windowYears,
  onWindowChange,
}) => {
  const {
    sample_count,
    mean_return_pct,
    median_return_pct,
    p25_return_pct,
    p75_return_pct,
    min_return_pct,
    max_return_pct,
    negative_return_prob_pct,
    outperformance_pct,
  } = rollingReturns;

  // Box plot dimensions & scale
  const spanMin = Math.min(min_return_pct, -5);
  const spanMax = Math.max(max_return_pct, 25);
  const totalSpan = spanMax - spanMin || 1;

  const toPct = (val: number) => {
    const clamped = Math.max(spanMin, Math.min(spanMax, val));
    return ((clamped - spanMin) / totalSpan) * 100;
  };

  const zeroPos = toPct(0);
  const minPos = toPct(min_return_pct);
  const maxPos = toPct(max_return_pct);
  const p25Pos = toPct(p25_return_pct);
  const p75Pos = toPct(p75_return_pct);
  const medianPos = toPct(median_return_pct);

  return (
    <div className="bg-slate-900/70 rounded-2xl border border-slate-800/80 p-5 space-y-4 shadow-lg">
      {/* Header with Window Selector */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/70 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400">
            <RotateCcw className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              {windowYears}-Year Rolling Returns Distribution
            </h3>
            <p className="text-[11px] text-slate-400">
              Evaluated over {sample_count.toLocaleString('en-IN')} rolling observation windows
            </p>
          </div>
        </div>

        {onWindowChange && (
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
            {[1, 3, 5, 7].map((w) => (
              <button
                key={w}
                onClick={() => onWindowChange(w)}
                className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg transition-all ${
                  windowYears === w
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {w}Y
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
          <span className="text-[10px] text-slate-400 uppercase font-medium">Median CAGR</span>
          <p className="text-lg font-black text-emerald-400 mt-0.5">{median_return_pct}%</p>
          <span className="text-[10px] text-slate-400">50th Percentile</span>
        </div>

        <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
          <span className="text-[10px] text-slate-400 uppercase font-medium">Average (Mean)</span>
          <p className="text-lg font-bold text-white mt-0.5">{mean_return_pct}%</p>
          <span className="text-[10px] text-slate-400">Mean CAGR</span>
        </div>

        <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
          <span className="text-[10px] text-slate-400 uppercase font-medium">Core 50% Band</span>
          <p className="text-xs font-bold text-sky-300 mt-1.5">
            {p25_return_pct}% to {p75_return_pct}%
          </p>
          <span className="text-[10px] text-slate-400">P25 - P75 Range</span>
        </div>

        <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
          <span className="text-[10px] text-slate-400 uppercase font-medium">Full Spread</span>
          <p className="text-xs font-bold text-slate-300 mt-1.5">
            {min_return_pct}% / {max_return_pct}%
          </p>
          <span className="text-[10px] text-slate-400">Min / Max Recorded</span>
        </div>
      </div>

      {/* Visual Box-Whisker & Percentile Range Graphic */}
      <div className="bg-slate-950/80 rounded-xl border border-slate-800/80 p-4 space-y-3">
        <div className="flex justify-between items-center text-[11px]">
          <span className="text-slate-400 font-medium">Percentile Distribution Spread:</span>
          <span className="text-emerald-400 font-mono font-bold">
            P50 Median: {median_return_pct}%
          </span>
        </div>

        {/* Box Chart Track */}
        <div className="relative h-10 w-full flex items-center select-none">
          {/* Zero baseline */}
          <div
            className="absolute top-0 bottom-0 w-px bg-slate-700/80 z-0"
            style={{ left: `${zeroPos}%` }}
            title="0% Return Baseline"
          />

          {/* Min to Max Whisker Line */}
          <div
            className="absolute h-1 bg-slate-700 rounded-full"
            style={{
              left: `${minPos}%`,
              width: `${Math.max(1, maxPos - minPos)}%`,
            }}
          />

          {/* Whisker End Caps */}
          <div
            className="absolute h-3 w-1 bg-slate-500 rounded-sm -ml-0.5"
            style={{ left: `${minPos}%` }}
            title={`Minimum: ${min_return_pct}%`}
          />
          <div
            className="absolute h-3 w-1 bg-slate-500 rounded-sm -ml-0.5"
            style={{ left: `${maxPos}%` }}
            title={`Maximum: ${max_return_pct}%`}
          />

          {/* Interquartile Range (P25 - P75) Box */}
          <div
            className="absolute h-6 rounded-md bg-gradient-to-r from-sky-500/30 via-emerald-500/30 to-sky-500/30 border border-emerald-400/50 flex items-center justify-center shadow-md shadow-emerald-500/10"
            style={{
              left: `${p25Pos}%`,
              width: `${Math.max(2, p75Pos - p25Pos)}%`,
            }}
          >
            <span className="text-[9px] font-bold text-emerald-300 opacity-80 hidden sm:inline">
              50% Probability Range
            </span>
          </div>

          {/* Median Marker Needle */}
          <div
            className="absolute h-8 w-1 bg-amber-400 rounded-full -ml-0.5 z-10 shadow-lg shadow-amber-500/50"
            style={{ left: `${medianPos}%` }}
            title={`Median: ${median_return_pct}%`}
          />
        </div>

        {/* Labels below scale */}
        <div className="flex justify-between text-[10px] text-slate-500 font-mono">
          <span>Min: {min_return_pct}%</span>
          <span>0%</span>
          <span>Median: {median_return_pct}%</span>
          <span>Max: {max_return_pct}%</span>
        </div>
      </div>

      {/* Bottom Insights Bar: Downside Risk & Outperformance */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
        {/* Negative Return Probability Alert */}
        <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <ShieldCheck
              className={`h-4 w-4 ${
                negative_return_prob_pct === 0 ? 'text-emerald-400' : 'text-amber-400'
              }`}
            />
            <span className="text-slate-300">Negative Return Risk:</span>
          </div>
          <span
            className={`font-bold px-2 py-0.5 rounded text-[11px] ${
              negative_return_prob_pct === 0
                ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
            }`}
          >
            {negative_return_prob_pct}% (0 loss risk in {windowYears}Y)
          </span>
        </div>

        {/* Outperformance vs Benchmark */}
        <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300">Beat Benchmark:</span>
          </div>
          <span className="font-bold text-emerald-400 text-[11px] px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30">
            {outperformance_pct !== null && outperformance_pct !== undefined
              ? `${outperformance_pct}% of the time`
              : 'Consistent Alpha'}
          </span>
        </div>
      </div>
    </div>
  );
};
