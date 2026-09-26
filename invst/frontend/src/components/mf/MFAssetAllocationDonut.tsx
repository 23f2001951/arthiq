import React, { useState } from 'react';
import { PieChart } from 'lucide-react';

interface MFAssetAllocationDonutProps {
  allocation: Record<string, number>;
  title?: string;
  subtitle?: string;
  totalAmount?: number;
  currencyPrefix?: string;
}

export const MFAssetAllocationDonut: React.FC<MFAssetAllocationDonutProps> = ({
  allocation,
  title = 'Asset Allocation Architecture',
  subtitle = 'Category risk budgeting and asset class distribution',
  totalAmount,
  currencyPrefix = '₹',
}) => {
  const [hoveredCategory, setHoveredCategory] = useState<string | null>(null);

  const entries = Object.entries(allocation).filter(([, val]) => val > 0);
  const total = entries.reduce((acc, [, val]) => acc + val, 0) || 1;

  const colorPalette = [
    { stroke: '#10b981', dot: 'bg-emerald-400', badge: 'text-emerald-300 bg-emerald-500/15 border-emerald-500/30' },
    { stroke: '#0ea5e9', dot: 'bg-sky-400', badge: 'text-sky-300 bg-sky-500/15 border-sky-500/30' },
    { stroke: '#f59e0b', dot: 'bg-amber-400', badge: 'text-amber-300 bg-amber-500/15 border-amber-500/30' },
    { stroke: '#8b5cf6', dot: 'bg-purple-400', badge: 'text-purple-300 bg-purple-500/15 border-purple-500/30' },
    { stroke: '#f43f5e', dot: 'bg-rose-400', badge: 'text-rose-300 bg-rose-500/15 border-rose-500/30' },
    { stroke: '#14b8a6', dot: 'bg-teal-400', badge: 'text-teal-300 bg-teal-500/15 border-teal-500/30' },
    { stroke: '#6366f1', dot: 'bg-indigo-400', badge: 'text-indigo-300 bg-indigo-500/15 border-indigo-500/30' },
  ];

  // SVG Donut Calculations
  const radius = 64;
  const strokeWidth = 18;
  const circumference = 2 * Math.PI * radius;

  let cumulativeOffset = 0;
  const donutSegments = entries.map(([category, val], idx) => {
    const pct = val / total;
    const strokeDasharray = `${pct * circumference} ${circumference}`;
    const strokeDashoffset = -cumulativeOffset * circumference;
    cumulativeOffset += pct;
    const color = colorPalette[idx % colorPalette.length];
    return {
      category,
      val,
      pct: pct * 100,
      strokeDasharray,
      strokeDashoffset,
      color,
    };
  });

  const activeSegment = hoveredCategory
    ? donutSegments.find((s) => s.category === hoveredCategory) || donutSegments[0]
    : donutSegments[0];

  return (
    <div className="bg-slate-900/70 rounded-2xl border border-slate-800/80 p-5 space-y-4 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/70 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <PieChart className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">{title}</h3>
            <p className="text-[11px] text-slate-400">{subtitle}</p>
          </div>
        </div>
        <span className="text-[10px] font-mono text-purple-300 px-2 py-0.5 rounded bg-purple-500/10 border border-purple-500/20">
          {entries.length} Categories
        </span>
      </div>

      {/* Donut and Legend Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-12 gap-5 items-center">
        {/* Donut Ring with Center Readout */}
        <div className="sm:col-span-5 flex flex-col items-center justify-center">
          <div className="relative w-44 h-44 flex items-center justify-center select-none">
            <svg viewBox="0 0 170 170" className="w-full h-full -rotate-90">
              {/* Background Track */}
              <circle
                cx="85"
                cy="85"
                r={radius}
                fill="none"
                stroke="rgba(255, 255, 255, 0.06)"
                strokeWidth={strokeWidth}
              />

              {/* Segments */}
              {donutSegments.map((seg) => {
                const isHovered = hoveredCategory === seg.category;
                return (
                  <circle
                    key={seg.category}
                    cx="85"
                    cy="85"
                    r={radius}
                    fill="none"
                    stroke={seg.color.stroke}
                    strokeWidth={isHovered ? strokeWidth + 4 : strokeWidth}
                    strokeDasharray={seg.strokeDasharray}
                    strokeDashoffset={seg.strokeDashoffset}
                    strokeLinecap="round"
                    className="cursor-pointer transition-all duration-300"
                    style={{
                      opacity: hoveredCategory && !isHovered ? 0.35 : 1.0,
                    }}
                    onMouseEnter={() => setHoveredCategory(seg.category)}
                    onMouseLeave={() => setHoveredCategory(null)}
                  />
                );
              })}
            </svg>

            {/* Center Summary */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none px-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tight line-clamp-1">
                {activeSegment ? activeSegment.category.replace('Equity: ', '').replace('Debt: ', '').replace('Hybrid: ', '') : 'Allocation'}
              </span>
              <p className="text-xl font-black text-white mt-0.5">
                {activeSegment ? `${activeSegment.pct.toFixed(0)}%` : '100%'}
              </p>
              {totalAmount && activeSegment && (
                <span className="text-[10px] text-emerald-400 font-mono mt-0.5">
                  {currencyPrefix}{((totalAmount * activeSegment.pct) / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Legend List */}
        <div className="sm:col-span-7 space-y-2">
          {donutSegments.map((seg) => {
            const isHovered = hoveredCategory === seg.category;
            return (
              <div
                key={seg.category}
                onMouseEnter={() => setHoveredCategory(seg.category)}
                onMouseLeave={() => setHoveredCategory(null)}
                className={`p-2.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between gap-2 ${
                  isHovered
                    ? 'bg-slate-800/80 border-slate-700 shadow-md scale-[1.01]'
                    : 'bg-slate-950/50 border-slate-800/60 hover:bg-slate-900/50'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className="h-3 w-3 rounded-full shrink-0"
                    style={{ backgroundColor: seg.color.stroke }}
                  />
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-white truncate">
                      {seg.category}
                    </p>
                    {totalAmount && (
                      <p className="text-[10px] text-slate-400 font-mono">
                        {currencyPrefix}{((totalAmount * seg.pct) / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </p>
                    )}
                  </div>
                </div>

                <span className="text-xs font-bold font-mono text-slate-200 shrink-0">
                  {seg.pct.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
