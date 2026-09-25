import React, { useState, useMemo } from 'react';
import { TrendingUp, ShieldAlert, Award, Calendar, Zap } from 'lucide-react';

interface EquityChartProps {
  dates: string[];
  portfolioValues: number[];
  benchmarkValues: number[];
  benchmarkLabel?: string;
}

export const EquityChart: React.FC<EquityChartProps> = ({
  dates,
  portfolioValues,
  benchmarkValues,
  benchmarkLabel = 'NIFTY 500',
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [timeRange, setTimeRange] = useState<'1Y' | '3Y' | '5Y' | 'ALL'>('ALL');
  const [showDrawdown, setShowDrawdown] = useState<boolean>(true);

  // Slice data based on selected time range
  const filteredData = useMemo(() => {
    if (!dates || dates.length === 0) return { dates: [], pVals: [], bVals: [] };

    let count = dates.length;
    if (timeRange === '1Y') count = Math.min(252, dates.length);
    else if (timeRange === '3Y') count = Math.min(252 * 3, dates.length);
    else if (timeRange === '5Y') count = Math.min(252 * 5, dates.length);

    const startIdx = dates.length - count;
    return {
      dates: dates.slice(startIdx),
      pVals: portfolioValues.slice(startIdx),
      bVals: benchmarkValues.slice(startIdx),
    };
  }, [dates, portfolioValues, benchmarkValues, timeRange]);

  const { dates: curDates, pVals, bVals } = filteredData;

  // Calculate drawdowns
  const drawdowns = useMemo(() => {
    let peak = pVals[0] || 1;
    return pVals.map((v) => {
      if (v > peak) peak = v;
      return ((v - peak) / peak) * 100;
    });
  }, [pVals]);

  if (!curDates || curDates.length === 0 || pVals.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-sm text-slate-500 glass-panel rounded-2xl border border-white/[0.06]">
        <Zap className="w-8 h-8 text-slate-600 mb-2 animate-pulse" />
        <span>No equity curve data available for this range</span>
      </div>
    );
  }

  // Normalize equity series so both start at 100
  const pBase = pVals[0] || 1;
  const bBase = bVals[0] || 1;
  const pNorm = pVals.map((v) => (v / pBase) * 100);
  const bNorm = bVals.map((v) => (v / bBase) * 100);

  const allVals = [...pNorm, ...bNorm];
  const minVal = Math.min(...allVals) * 0.96;
  const maxVal = Math.max(...allVals) * 1.04;
  const range = maxVal - minVal || 1;

  const minDD = Math.min(...drawdowns, -5);

  const width = 880;
  const mainHeight = 290;
  const ddHeight = showDrawdown ? 95 : 0;
  const totalHeight = mainHeight + ddHeight + 16;
  const padding = { top: 24, right: 30, bottom: 32, left: 60 };
  const chartW = width - padding.left - padding.right;
  const mainChartH = mainHeight - padding.top - padding.bottom;

  const getX = (idx: number) => padding.left + (idx / (curDates.length - 1 || 1)) * chartW;
  const getY = (val: number) => padding.top + mainChartH - ((val - minVal) / range) * mainChartH;
  const getDDY = (val: number) => mainHeight + 12 + (Math.abs(val) / Math.abs(minDD || 1)) * (ddHeight - 30);

  // Smooth spline generator (Catmull-Rom to Cubic Bezier)
  const buildSmoothPath = (series: number[]) => {
    if (series.length === 0) return '';
    if (series.length === 1) return `M ${getX(0).toFixed(1)},${getY(series[0]).toFixed(1)}`;

    const points = series.map((val, idx) => ({ x: getX(idx), y: getY(val) }));
    let path = `M ${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;

    for (let i = 0; i < points.length - 1; i++) {
      const p0 = i > 0 ? points[i - 1] : points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = i < points.length - 2 ? points[i + 2] : p2;

      const tension = 0.18;
      const cp1x = p1.x + (p2.x - p0.x) * tension;
      const cp1y = p1.y + (p2.y - p0.y) * tension;
      const cp2x = p2.x - (p3.x - p1.x) * tension;
      const cp2y = p2.y - (p3.y - p1.y) * tension;

      path += ` C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return path;
  };

  const buildSmoothDrawdownPath = (dd: number[]) => {
    if (dd.length === 0) return '';
    const points = dd.map((val, idx) => ({ x: getX(idx), y: getDDY(val) }));
    let path = `M ${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;

    for (let i = 0; i < points.length - 1; i++) {
      const p0 = i > 0 ? points[i - 1] : points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = i < points.length - 2 ? points[i + 2] : p2;

      const tension = 0.18;
      const cp1x = p1.x + (p2.x - p0.x) * tension;
      const cp1y = p1.y + (p2.y - p0.y) * tension;
      const cp2x = p2.x - (p3.x - p1.x) * tension;
      const cp2y = p2.y - (p3.y - p1.y) * tension;

      path += ` C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return path;
  };

  const pPath = buildSmoothPath(pNorm);
  const bPath = buildSmoothPath(bNorm);

  // Strategy Area Fill
  const pArea = `${pPath} L ${getX(curDates.length - 1).toFixed(1)},${padding.top + mainChartH} L ${getX(0).toFixed(1)},${padding.top + mainChartH} Z`;

  // Drawdown Area Fill
  const ddSmoothLine = showDrawdown ? buildSmoothDrawdownPath(drawdowns) : '';
  const ddArea = showDrawdown
    ? `M ${getX(0).toFixed(1)},${mainHeight + 12} ` +
      ddSmoothLine.replace(/^M [^ ]+ /, 'L ') +
      ` L ${getX(curDates.length - 1).toFixed(1)},${mainHeight + 12} Z`
    : '';

  // Calculate Peak & Max Drawdown indices
  const maxPIdx = useMemo(() => {
    let maxV = -Infinity;
    let idx = 0;
    pNorm.forEach((v, i) => {
      if (v > maxV) {
        maxV = v;
        idx = i;
      }
    });
    return idx;
  }, [pNorm]);

  const maxDDIdx = useMemo(() => {
    let minD = Infinity;
    let idx = 0;
    drawdowns.forEach((d, i) => {
      if (d < minD) {
        minD = d;
        idx = i;
      }
    });
    return idx;
  }, [drawdowns]);

  const activeIdx = hoverIndex !== null ? hoverIndex : curDates.length - 1;
  const activeDate = curDates[activeIdx];
  const activeP = pVals[activeIdx];
  const activeB = bVals[activeIdx];
  const activePNorm = pNorm[activeIdx];
  const activeBNorm = bNorm[activeIdx];
  const activeDD = drawdowns[activeIdx];

  const pTotalRet = pNorm[pNorm.length - 1] - 100;
  const bTotalRet = bNorm[bNorm.length - 1] - 100;
  const alpha = pTotalRet - bTotalRet;

  // Y-axis ticks
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const val = minVal + ratio * range;
    return { val: val.toFixed(0), y: getY(val) };
  });

  // X-axis ticks (5 evenly spaced dates)
  const xIndices = [
    0,
    Math.floor(curDates.length * 0.25),
    Math.floor(curDates.length * 0.5),
    Math.floor(curDates.length * 0.75),
    curDates.length - 1,
  ];

  return (
    <div className="glass-panel p-6 rounded-3xl relative overflow-hidden space-y-4">
      {/* Background ambient beam */}
      <div className="absolute top-0 right-1/4 w-96 h-40 bg-emerald-500/5 blur-3xl pointer-events-none" />

      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-white/[0.08] relative z-10">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <TrendingUp className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-extrabold tracking-tight text-white flex items-center">
                Cumulative Equity &amp; Underwater Drawdown
                <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-mono">
                  Base 100
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Walk-forward cumulative net-of-costs performance vs benchmark
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 mt-3 text-xs">
            {/* Strategy Pill */}
            <div className="flex items-center space-x-2 px-2.5 py-1 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 font-bold font-mono">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
              <span>Strategy: {pTotalRet >= 0 ? `+${pTotalRet.toFixed(1)}%` : `${pTotalRet.toFixed(1)}%`}</span>
            </div>

            {/* Benchmark Pill */}
            <div className="flex items-center space-x-2 px-2.5 py-1 rounded-lg bg-slate-900/60 border border-slate-700/60 text-slate-300 font-medium font-mono">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
              <span>{benchmarkLabel}: {bTotalRet >= 0 ? `+${bTotalRet.toFixed(1)}%` : `${bTotalRet.toFixed(1)}%`}</span>
            </div>

            {/* Alpha Badge */}
            <div
              className={`px-2.5 py-1 rounded-lg font-bold text-xs font-mono flex items-center space-x-1.5 ${
                alpha >= 0
                  ? 'bg-sky-500/15 text-sky-300 border border-sky-500/30'
                  : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
              }`}
            >
              <Award className="w-3.5 h-3.5" />
              <span>Alpha: {alpha >= 0 ? `+${alpha.toFixed(1)}%` : `${alpha.toFixed(1)}%`}</span>
            </div>
          </div>
        </div>

        {/* Toolbar: Timeframe & Drawdown Toggle */}
        <div className="flex items-center space-x-2.5">
          {/* Timeframe selector */}
          <div className="flex items-center p-1 bg-[#05070d] rounded-xl border border-white/[0.08] shadow-inner text-xs">
            {(['1Y', '3Y', '5Y', 'ALL'] as const).map((rangeKey) => (
              <button
                key={rangeKey}
                onClick={() => setTimeRange(rangeKey)}
                className={`px-3 py-1 rounded-lg font-mono font-bold transition-all duration-200 cursor-pointer ${
                  timeRange === rangeKey
                    ? 'bg-gradient-to-r from-emerald-500 to-teal-400 text-slate-950 shadow-[0_0_12px_rgba(16,185,129,0.4)]'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {rangeKey}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowDrawdown(!showDrawdown)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold transition-all cursor-pointer ${
              showDrawdown
                ? 'bg-rose-950/40 border-rose-700/60 text-rose-300 shadow-[0_0_12px_rgba(244,63,94,0.25)]'
                : 'bg-[#05070d] border-white/[0.08] text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Drawdown</span>
          </button>
        </div>
      </div>

      {/* Interactive HUD Readout Banner */}
      <div className="flex flex-wrap items-center justify-between p-3.5 rounded-2xl bg-[#070912]/90 border border-white/[0.08] text-xs shadow-lg backdrop-blur-md">
        <div className="flex items-center space-x-2">
          <Calendar className="w-3.5 h-3.5 text-sky-400" />
          <span className="font-mono font-bold text-white text-xs">{activeDate}</span>
          {activeIdx === curDates.length - 1 && (
            <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              LATEST
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-4 sm:gap-6 font-mono text-xs">
          <div>
            <span className="text-slate-400 mr-1.5">Strategy NAV:</span>
            <span className="font-bold text-emerald-400">
              ₹{activeP.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </span>
            <span className="text-slate-500 ml-1">({activePNorm.toFixed(1)})</span>
          </div>
          <div>
            <span className="text-slate-400 mr-1.5">{benchmarkLabel}:</span>
            <span className="font-bold text-slate-300">
              ₹{activeB.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </span>
            <span className="text-slate-500 ml-1">({activeBNorm.toFixed(1)})</span>
          </div>
          {showDrawdown && (
            <div>
              <span className="text-slate-400 mr-1.5">Underwater DD:</span>
              <span className={`font-bold ${activeDD < -10 ? 'text-rose-400' : 'text-amber-400'}`}>
                {activeDD.toFixed(2)}%
              </span>
            </div>
          )}
        </div>
      </div>

      {/* High-Performance SVG Chart */}
      <div className="relative w-full overflow-hidden select-none">
        <svg
          viewBox={`0 0 ${width} ${totalHeight}`}
          className="w-full h-auto"
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const relX = ((e.clientX - rect.left) / rect.width) * width - padding.left;
            const idx = Math.round((relX / chartW) * (curDates.length - 1));
            if (idx >= 0 && idx < curDates.length) {
              setHoverIndex(idx);
            }
          }}
          onMouseLeave={() => {
            setHoverIndex(null);
          }}
        >
          <defs>
            {/* Strategy Glowing Gradient Fill */}
            <linearGradient id="eqStrategyGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.32" />
              <stop offset="60%" stopColor="#06b6d4" stopOpacity="0.08" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
            </linearGradient>

            {/* Drawdown Area Gradient */}
            <linearGradient id="eqDrawdownGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.0" />
              <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.4" />
            </linearGradient>

            {/* Neon Glow Filters */}
            <filter id="emeraldLineGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#10b981" floodOpacity="0.6" />
            </filter>
            <filter id="skyLineGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#38bdf8" floodOpacity="0.6" />
            </filter>
          </defs>

          {/* Grid lines */}
          {yTicks.map((t, i) => (
            <g key={i}>
              <line
                x1={padding.left}
                y1={t.y}
                x2={width - padding.right}
                y2={t.y}
                stroke="#172033"
                strokeDasharray="4 4"
                strokeWidth="1"
              />
              <text
                x={padding.left - 10}
                y={t.y + 4}
                textAnchor="end"
                fontSize="10"
                fill="#64748b"
                fontFamily="monospace"
                fontWeight="600"
              >
                {t.val}
              </text>
            </g>
          ))}

          {/* Strategy Gradient Fill Area */}
          <path d={pArea} fill="url(#eqStrategyGrad)" />

          {/* Benchmark line */}
          <path
            d={bPath}
            fill="none"
            stroke="#64748b"
            strokeWidth="1.75"
            strokeDasharray="4 4"
            className="transition-all"
          />

          {/* Portfolio Strategy Line with glow filter */}
          <path
            d={pPath}
            fill="none"
            stroke="#10b981"
            strokeWidth="2.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#emeraldLineGlow)"
            className="transition-all"
          />

          {/* Peak ATH Marker on Strategy Line */}
          {maxPIdx >= 0 && maxPIdx < curDates.length && (
            <g>
              <circle
                cx={getX(maxPIdx)}
                cy={getY(pNorm[maxPIdx])}
                r="4"
                fill="#34d399"
                stroke="#064e3b"
                strokeWidth="2"
              />
              <rect
                x={getX(maxPIdx) - 22}
                y={getY(pNorm[maxPIdx]) - 20}
                width="44"
                height="14"
                rx="4"
                fill="#064e3b"
                stroke="#34d399"
                strokeWidth="1"
              />
              <text
                x={getX(maxPIdx)}
                y={getY(pNorm[maxPIdx]) - 10}
                textAnchor="middle"
                fontSize="8"
                fill="#a7f3d0"
                fontFamily="monospace"
                fontWeight="bold"
              >
                ATH PEAK
              </text>
            </g>
          )}

          {/* Underwater Drawdown Section */}
          {showDrawdown && (
            <g>
              {/* Separator / 0% Waterline */}
              <line
                x1={padding.left}
                y1={mainHeight + 12}
                x2={width - padding.right}
                y2={mainHeight + 12}
                stroke="#334155"
                strokeWidth="1.2"
                strokeDasharray="3 3"
              />
              <text
                x={padding.left - 10}
                y={mainHeight + 16}
                textAnchor="end"
                fontSize="9"
                fill="#94a3b8"
                fontFamily="monospace"
                fontWeight="bold"
              >
                0%
              </text>
              <text
                x={padding.left - 10}
                y={mainHeight + ddHeight}
                textAnchor="end"
                fontSize="9"
                fill="#f43f5e"
                fontFamily="monospace"
                fontWeight="bold"
              >
                {minDD.toFixed(0)}%
              </text>

              {/* Drawdown Area & Smooth Line */}
              <path d={ddArea} fill="url(#eqDrawdownGrad)" />
              <path
                d={ddSmoothLine}
                fill="none"
                stroke="#f43f5e"
                strokeWidth="1.75"
                strokeLinecap="round"
              />

              {/* Max Drawdown Trough Flag */}
              {maxDDIdx >= 0 && maxDDIdx < curDates.length && minDD < -3 && (
                <g>
                  <circle
                    cx={getX(maxDDIdx)}
                    cy={getDDY(drawdowns[maxDDIdx])}
                    r="3.5"
                    fill="#f43f5e"
                    stroke="#450a0a"
                    strokeWidth="2"
                  />
                  <rect
                    x={getX(maxDDIdx) - 26}
                    y={getDDY(drawdowns[maxDDIdx]) + 6}
                    width="52"
                    height="14"
                    rx="4"
                    fill="#450a0a"
                    stroke="#f43f5e"
                    strokeWidth="1"
                  />
                  <text
                    x={getX(maxDDIdx)}
                    y={getDDY(drawdowns[maxDDIdx]) + 16}
                    textAnchor="middle"
                    fontSize="8"
                    fill="#fecdd3"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    MAX DD {drawdowns[maxDDIdx].toFixed(1)}%
                  </text>
                </g>
              )}
            </g>
          )}

          {/* Dates along X axis */}
          {xIndices.map((idx) => {
            if (!curDates[idx]) return null;
            return (
              <text
                key={idx}
                x={getX(idx)}
                y={totalHeight - 4}
                textAnchor="middle"
                fontSize="10"
                fill="#64748b"
                fontFamily="monospace"
                fontWeight="600"
              >
                {curDates[idx]}
              </text>
            );
          })}

          {/* Hover Crosshair & Pointer Dots */}
          {hoverIndex !== null && (
            <g>
              {/* Vertical Guide Line */}
              <line
                x1={getX(hoverIndex)}
                y1={padding.top}
                x2={getX(hoverIndex)}
                y2={showDrawdown ? mainHeight + ddHeight : mainHeight - padding.bottom}
                stroke="#38bdf8"
                strokeWidth="1.2"
                strokeDasharray="3 3"
              />

              {/* Portfolio Node */}
              <circle
                cx={getX(hoverIndex)}
                cy={getY(pNorm[hoverIndex])}
                r="6"
                fill="#10b981"
                stroke="#042f2e"
                strokeWidth="3"
                className="animate-pulse"
              />

              {/* Benchmark Node */}
              <circle
                cx={getX(hoverIndex)}
                cy={getY(bNorm[hoverIndex])}
                r="4.5"
                fill="#94a3b8"
                stroke="#0f172a"
                strokeWidth="2.5"
              />

              {/* Drawdown Node */}
              {showDrawdown && (
                <circle
                  cx={getX(hoverIndex)}
                  cy={getDDY(drawdowns[hoverIndex])}
                  r="4.5"
                  fill="#f43f5e"
                  stroke="#450a0a"
                  strokeWidth="2"
                />
              )}
            </g>
          )}
        </svg>
      </div>
    </div>
  );
};

export default EquityChart;
