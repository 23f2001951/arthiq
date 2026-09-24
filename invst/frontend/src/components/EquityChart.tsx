import React, { useState, useMemo } from 'react';
import { TrendingUp, ShieldAlert, Award, Calendar } from 'lucide-react';

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
      <div className="h-64 flex items-center justify-center text-sm text-slate-500 glass-card rounded-2xl border border-slate-800">
        No equity curve data available
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

  const width = 850;
  const mainHeight = 280;
  const ddHeight = showDrawdown ? 90 : 0;
  const totalHeight = mainHeight + ddHeight + 10;
  const padding = { top: 20, right: 25, bottom: 30, left: 55 };
  const chartW = width - padding.left - padding.right;
  const mainChartH = mainHeight - padding.top - padding.bottom;

  const getX = (idx: number) => padding.left + (idx / (curDates.length - 1 || 1)) * chartW;
  const getY = (val: number) => padding.top + mainChartH - ((val - minVal) / range) * mainChartH;
  const getDDY = (val: number) => mainHeight + 10 + (Math.abs(val) / Math.abs(minDD || 1)) * (ddHeight - 25);

  const buildPath = (series: number[]) => {
    return series
      .map((val, idx) => `${idx === 0 ? 'M' : 'L'} ${getX(idx).toFixed(1)},${getY(val).toFixed(1)}`)
      .join(' ');
  };

  const pPath = buildPath(pNorm);
  const bPath = buildPath(bNorm);

  // Strategy Area Fill
  const pArea = `${pPath} L ${getX(curDates.length - 1)},${padding.top + mainChartH} L ${getX(0)},${padding.top + mainChartH} Z`;

  // Drawdown Area Fill
  const ddArea = showDrawdown
    ? `M ${getX(0)},${mainHeight + 10} ` +
      drawdowns.map((d, i) => `L ${getX(i).toFixed(1)},${getDDY(d).toFixed(1)}`).join(' ') +
      ` L ${getX(curDates.length - 1)},${mainHeight + 10} Z`
    : '';

  const activeIdx = hoverIndex !== null ? hoverIndex : curDates.length - 1;
  const activeDate = curDates[activeIdx];
  const activeP = pVals[activeIdx];
  const activeB = bVals[activeIdx];
  const activePNorm = pNorm[activeIdx];
  const activeBNorm = bNorm[activeIdx];
  const activeDD = drawdowns[activeIdx];

  const pTotalRet = (pNorm[pNorm.length - 1] - 100);
  const bTotalRet = (bNorm[bNorm.length - 1] - 100);
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
    <div className="glass-card rounded-2xl p-6 border border-slate-800 shadow-2xl space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-black tracking-tight text-white flex items-center">
              <TrendingUp className="w-5 h-5 mr-2 text-emerald-400" />
              Cumulative Equity & Underwater Drawdown
            </h3>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
              Indexed (Base 100)
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 mt-2 text-xs">
            {/* Strategy Pill */}
            <div className="flex items-center space-x-1.5 font-bold text-emerald-400">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-md shadow-emerald-400/50" />
              <span>Strategy: {pTotalRet >= 0 ? `+${pTotalRet.toFixed(1)}%` : `${pTotalRet.toFixed(1)}%`}</span>
            </div>

            {/* Benchmark Pill */}
            <div className="flex items-center space-x-1.5 font-medium text-slate-400">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-500" />
              <span>{benchmarkLabel}: {bTotalRet >= 0 ? `+${bTotalRet.toFixed(1)}%` : `${bTotalRet.toFixed(1)}%`}</span>
            </div>

            {/* Alpha Badge */}
            <div className={`px-2 py-0.5 rounded-full font-bold text-[11px] flex items-center space-x-1 ${
              alpha >= 0 ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-300 border border-rose-500/30'
            }`}>
              <Award className="w-3 h-3 mr-0.5" />
              <span>Alpha: {alpha >= 0 ? `+${alpha.toFixed(1)}%` : `${alpha.toFixed(1)}%`}</span>
            </div>
          </div>
        </div>

        {/* Toolbar: Timeframe & Drawdown Toggle */}
        <div className="flex items-center space-x-2">
          {/* Timeframe selector */}
          <div className="flex items-center p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs">
            {(['1Y', '3Y', '5Y', 'ALL'] as const).map((rangeKey) => (
              <button
                key={rangeKey}
                onClick={() => setTimeRange(rangeKey)}
                className={`px-2.5 py-1 rounded-lg font-bold transition-all ${
                  timeRange === rangeKey
                    ? 'bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {rangeKey}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowDrawdown(!showDrawdown)}
            className={`flex items-center space-x-1 px-3 py-1.5 rounded-xl border text-xs font-bold transition-colors ${
              showDrawdown
                ? 'bg-rose-950/40 border-rose-800 text-rose-300'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Drawdown</span>
          </button>
        </div>
      </div>

      {/* Floating Hover Crosshair Inspector Card */}
      <div className="flex flex-wrap items-center justify-between p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-xs">
        <div className="flex items-center space-x-2">
          <Calendar className="w-3.5 h-3.5 text-slate-500" />
          <span className="font-mono font-bold text-white">{activeDate}</span>
        </div>
        <div className="flex items-center space-x-5 font-mono text-xs">
          <div>
            <span className="text-slate-400 mr-1.5">Strategy:</span>
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
              <span className="text-slate-400 mr-1.5">DD:</span>
              <span className="font-bold text-rose-400">
                {activeDD.toFixed(2)}%
              </span>
            </div>
          )}
        </div>
      </div>

      {/* High-Performance SVG Chart */}
      <div className="relative w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${totalHeight}`}
          className="w-full h-auto select-none"
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const relX = ((e.clientX - rect.left) / rect.width) * width - padding.left;
            const idx = Math.round((relX / chartW) * (curDates.length - 1));
            if (idx >= 0 && idx < curDates.length) setHoverIndex(idx);
          }}
          onMouseLeave={() => setHoverIndex(null)}
        >
          <defs>
            {/* Strategy Glowing Gradient Fill */}
            <linearGradient id="strategyGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.30" />
              <stop offset="60%" stopColor="#06b6d4" stopOpacity="0.08" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
            </linearGradient>

            {/* Drawdown Area Gradient */}
            <linearGradient id="drawdownGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.0" />
              <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.35" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {yTicks.map((t, i) => (
            <g key={i}>
              <line
                x1={padding.left}
                y1={t.y}
                x2={width - padding.right}
                y2={t.y}
                stroke="#1e293b"
                strokeDasharray="3 3"
              />
              <text
                x={padding.left - 10}
                y={t.y + 4}
                textAnchor="end"
                fontSize="10"
                fill="#64748b"
                fontFamily="monospace"
              >
                {t.val}
              </text>
            </g>
          ))}

          {/* Strategy Gradient Fill */}
          <path d={pArea} fill="url(#strategyGrad)" />

          {/* Benchmark line */}
          <path
            d={bPath}
            fill="none"
            stroke="#64748b"
            strokeWidth="1.75"
            strokeDasharray="4 4"
            className="transition-all"
          />

          {/* Portfolio Strategy Line with glow */}
          <path
            d={pPath}
            fill="none"
            stroke="#10b981"
            strokeWidth="2.75"
            strokeLinecap="round"
            className="transition-all"
          />

          {/* Underwater Drawdown Section */}
          {showDrawdown && (
            <g>
              {/* Separator line */}
              <line
                x1={padding.left}
                y1={mainHeight + 10}
                x2={width - padding.right}
                y2={mainHeight + 10}
                stroke="#334155"
                strokeWidth="1"
              />
              <text
                x={padding.left - 10}
                y={mainHeight + 14}
                textAnchor="end"
                fontSize="9"
                fill="#94a3b8"
                fontFamily="monospace"
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
              >
                {minDD.toFixed(0)}%
              </text>

              {/* Drawdown Area */}
              <path d={ddArea} fill="url(#drawdownGrad)" />
              <path
                d={
                  `M ${getX(0)},${getDDY(drawdowns[0])} ` +
                  drawdowns.map((d, i) => `L ${getX(i).toFixed(1)},${getDDY(d).toFixed(1)}`).join(' ')
                }
                fill="none"
                stroke="#f43f5e"
                strokeWidth="1.5"
              />
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
              >
                {curDates[idx]}
              </text>
            );
          })}

          {/* Hover Crosshair & Pointer Dots */}
          {hoverIndex !== null && (
            <g>
              <line
                x1={getX(hoverIndex)}
                y1={padding.top}
                x2={getX(hoverIndex)}
                y2={showDrawdown ? mainHeight + ddHeight : mainHeight - padding.bottom}
                stroke="#38bdf8"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              {/* Portfolio Node */}
              <circle
                cx={getX(hoverIndex)}
                cy={getY(pNorm[hoverIndex])}
                r="5"
                fill="#10b981"
                stroke="#022c22"
                strokeWidth="2.5"
              />
              {/* Benchmark Node */}
              <circle
                cx={getX(hoverIndex)}
                cy={getY(bNorm[hoverIndex])}
                r="4"
                fill="#64748b"
                stroke="#0f172a"
                strokeWidth="2"
              />
              {showDrawdown && (
                <circle
                  cx={getX(hoverIndex)}
                  cy={getDDY(drawdowns[hoverIndex])}
                  r="3.5"
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
