import React, { useState, useMemo } from 'react';
import { TrendingUp } from 'lucide-react';

interface UnifiedTrajectoryPoint {
  year: number;
  monthly_sip: number;
  total_invested: number;
  corpus_base: number;
  corpus_bull?: number;
  corpus_bear?: number;
  real_purchasing_power: number;
}

interface MFWealthTrajectoryChartProps {
  trajectory: UnifiedTrajectoryPoint[];
  expectedCagr: number;
  bullCagr?: number;
  bearCagr?: number;
  stepUpPct?: number;
}

export const MFWealthTrajectoryChart: React.FC<MFWealthTrajectoryChartProps> = ({
  trajectory,
  expectedCagr,
  bullCagr = expectedCagr + 3.0,
  bearCagr = Math.max(expectedCagr - 3.5, 4.5),
  stepUpPct = 10,
}) => {
  const [hoverYearIndex, setHoverYearIndex] = useState<number | null>(null);

  const finalPoint = trajectory[trajectory.length - 1];

  // Find max value across all curves for scaling
  const maxVal = useMemo(() => {
    if (!trajectory || trajectory.length === 0) return 100000;
    let max = 0;
    trajectory.forEach((t) => {
      const bull = t.corpus_bull ?? t.corpus_base * 1.2;
      if (bull > max) max = bull;
      if (t.corpus_base > max) max = t.corpus_base;
    });
    return max * 1.08;
  }, [trajectory]);

  // Chart dimensions
  const width = 760;
  const height = 260;
  const padding = { top: 24, right: 24, bottom: 32, left: 64 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const getX = (idx: number) => padding.left + (idx / Math.max(1, trajectory.length - 1)) * chartW;
  const getY = (val: number) => padding.top + chartH - (val / (maxVal || 1)) * chartH;

  // Build Spline Paths
  const buildPath = (key: 'corpus_bull' | 'corpus_base' | 'corpus_bear' | 'total_invested' | 'real_purchasing_power') => {
    if (!trajectory || trajectory.length === 0) return '';
    const points = trajectory.map((t, idx) => {
      let val = t[key] ?? t.corpus_base;
      return { x: getX(idx), y: getY(val) };
    });

    let d = `M ${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = i > 0 ? points[i - 1] : points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = i < points.length - 2 ? points[i + 2] : p2;

      const tension = 0.16;
      const cp1x = p1.x + (p2.x - p0.x) * tension;
      const cp1y = p1.y + (p2.y - p0.y) * tension;
      const cp2x = p2.x - (p3.x - p1.x) * tension;
      const cp2y = p2.y - (p3.y - p1.y) * tension;

      d += ` C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return d;
  };

  const bullPath = useMemo(() => buildPath('corpus_bull'), [trajectory, maxVal]);
  const basePath = useMemo(() => buildPath('corpus_base'), [trajectory, maxVal]);
  const bearPath = useMemo(() => buildPath('corpus_bear'), [trajectory, maxVal]);
  const investedPath = useMemo(() => buildPath('total_invested'), [trajectory, maxVal]);
  const realPwrPath = useMemo(() => buildPath('real_purchasing_power'), [trajectory, maxVal]);

  // Base Area fill
  const baseAreaPath = useMemo(() => {
    if (!basePath || trajectory.length === 0) return '';
    const firstX = getX(0).toFixed(1);
    const lastX = getX(trajectory.length - 1).toFixed(1);
    const bottomY = (padding.top + chartH).toFixed(1);
    return `${basePath} L ${lastX},${bottomY} L ${firstX},${bottomY} Z`;
  }, [basePath, trajectory]);

  const activePoint = hoverYearIndex !== null && trajectory[hoverYearIndex] ? trajectory[hoverYearIndex] : finalPoint;

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (trajectory.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const svgX = (mouseX / rect.width) * width;
    const clampedX = Math.max(padding.left, Math.min(padding.left + chartW, svgX));
    const ratio = (clampedX - padding.left) / chartW;
    const idx = Math.round(ratio * (trajectory.length - 1));
    setHoverYearIndex(Math.max(0, Math.min(trajectory.length - 1, idx)));
  };

  const handleMouseLeave = () => {
    setHoverYearIndex(null);
  };

  return (
    <div className="bg-slate-900/70 rounded-2xl border border-slate-800/80 p-5 space-y-4 shadow-lg">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/70 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <TrendingUp className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              Multi-Scenario Wealth Accumulation Trajectory
            </h3>
            <p className="text-[11px] text-slate-400">
              Compounding fan chart with {stepUpPct}% annual SIP step-up &amp; inflation adjustments
            </p>
          </div>
        </div>

        {/* Legend Pills */}
        <div className="flex flex-wrap items-center gap-2 text-[10px] font-medium">
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
            <span className="h-2 w-2 rounded-full bg-sky-400" />
            Bull ({bullCagr}%)
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-bold">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Base ({expectedCagr}%)
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            Bear ({bearCagr}%)
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            <span className="h-1.5 w-3 border-t border-dashed border-slate-400" />
            Invested Capital
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
            <span className="h-2 w-2 rounded-full bg-purple-400" />
            Real Purchasing Power (6% Infl.)
          </span>
        </div>
      </div>

      {/* Snapshot Cards */}
      {activePoint && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 text-xs">
          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
            <span className="text-[10px] text-slate-400 uppercase font-medium">Timeline Marker</span>
            <p className="text-base font-extrabold text-white mt-0.5">Year {activePoint.year}</p>
            <span className="text-[10px] text-slate-400">
              SIP: ₹{activePoint.monthly_sip.toLocaleString('en-IN')}/mo
            </span>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
            <span className="text-[10px] text-slate-400 uppercase font-medium">Invested Capital</span>
            <p className="text-base font-bold text-slate-300 mt-0.5">
              ₹{(activePoint.total_invested / 100000).toFixed(2)} L
            </p>
            <span className="text-[10px] text-slate-500">Cumulative Deposits</span>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-emerald-500/40 bg-emerald-950/20">
            <span className="text-[10px] text-emerald-400 uppercase font-bold">Expected Corpus (Base)</span>
            <p className="text-lg font-black text-emerald-300 mt-0.5">
              ₹{(activePoint.corpus_base / 100000).toFixed(2)} L
            </p>
            <span className="text-[10px] text-emerald-400/80">
              {(activePoint.corpus_base / activePoint.total_invested).toFixed(2)}x Wealth Multiplier
            </span>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
            <span className="text-[10px] text-sky-400 uppercase font-medium">Bull Case (+3%)</span>
            <p className="text-base font-bold text-sky-300 mt-0.5">
              ₹{((activePoint.corpus_bull ?? activePoint.corpus_base * 1.2) / 100000).toFixed(2)} L
            </p>
            <span className="text-[10px] text-slate-400">Optimistic High</span>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
            <span className="text-[10px] text-purple-400 uppercase font-medium">Real Purchasing Power</span>
            <p className="text-base font-bold text-purple-300 mt-0.5">
              ₹{(activePoint.real_purchasing_power / 100000).toFixed(2)} L
            </p>
            <span className="text-[10px] text-slate-400">After 6% Inflation</span>
          </div>
        </div>
      )}

      {/* SVG Canvas */}
      <div className="relative w-full overflow-hidden select-none">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible cursor-crosshair"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <defs>
            <linearGradient id="base-area-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.22" />
              <stop offset="90%" stopColor="#10b981" stopOpacity="0.02" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.00" />
            </linearGradient>
          </defs>

          {/* Horizontal Gridlines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
            const yVal = pct * maxVal;
            const yPos = getY(yVal);
            return (
              <g key={pct}>
                <line
                  x1={padding.left}
                  y1={yPos}
                  x2={width - padding.right}
                  y2={yPos}
                  stroke="rgba(255, 255, 255, 0.06)"
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={yPos + 3}
                  fill="rgba(148, 163, 184, 0.6)"
                  fontSize="9"
                  fontFamily="monospace"
                  textAnchor="end"
                >
                  ₹{(yVal / 100000).toFixed(1)}L
                </text>
              </g>
            );
          })}

          {/* Year Gridlines & Labels */}
          {trajectory.map((t, idx) => {
            const xPos = getX(idx);
            return (
              <text
                key={t.year}
                x={xPos}
                y={height - 10}
                fill="rgba(148, 163, 184, 0.6)"
                fontSize="9"
                fontFamily="monospace"
                textAnchor="middle"
              >
                Y{t.year}
              </text>
            );
          })}

          {/* Base Area Fill */}
          <path d={baseAreaPath} fill="url(#base-area-grad)" />

          {/* Bull Line */}
          <path
            d={bullPath}
            fill="none"
            stroke="#0ea5e9"
            strokeWidth="1.8"
            strokeDasharray="4 2"
            opacity="0.85"
          />

          {/* Bear Line */}
          <path
            d={bearPath}
            fill="none"
            stroke="#f59e0b"
            strokeWidth="1.8"
            strokeDasharray="4 2"
            opacity="0.85"
          />

          {/* Capital Invested Baseline */}
          <path
            d={investedPath}
            fill="none"
            stroke="#94a3b8"
            strokeWidth="1.5"
            strokeDasharray="2 2"
            opacity="0.7"
          />

          {/* Real Purchasing Power Line */}
          <path
            d={realPwrPath}
            fill="none"
            stroke="#a855f7"
            strokeWidth="1.8"
            opacity="0.8"
          />

          {/* Expected Base Curve (Highlighted) */}
          <path
            d={basePath}
            fill="none"
            stroke="#10b981"
            strokeWidth="2.8"
            strokeLinecap="round"
          />

          {/* Interactive Hover Crosshair */}
          {hoverYearIndex !== null && activePoint && (
            <g>
              <line
                x1={getX(hoverYearIndex)}
                y1={padding.top}
                x2={getX(hoverYearIndex)}
                y2={padding.top + chartH}
                stroke="rgba(255, 255, 255, 0.4)"
                strokeWidth="1.2"
                strokeDasharray="3 3"
              />

              {/* Point on Base */}
              <circle
                cx={getX(hoverYearIndex)}
                cy={getY(activePoint.corpus_base)}
                r="4.5"
                fill="#ffffff"
                stroke="#10b981"
                strokeWidth="2.5"
              />

              {/* Point on Invested */}
              <circle
                cx={getX(hoverYearIndex)}
                cy={getY(activePoint.total_invested)}
                r="3.5"
                fill="#94a3b8"
              />
            </g>
          )}
        </svg>
      </div>
    </div>
  );
};
