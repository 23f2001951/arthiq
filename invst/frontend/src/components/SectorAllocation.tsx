import React, { useState } from 'react';
import { PieChart, ShieldAlert } from 'lucide-react';

interface SectorAllocationProps {
  sectors: Record<string, number>;
}

export const SectorAllocation: React.FC<SectorAllocationProps> = ({ sectors }) => {
  const [hoveredSector, setHoveredSector] = useState<string | null>(null);

  const entries = Object.entries(sectors).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((acc, [, val]) => acc + val, 0) || 1;

  const colorPalette = [
    { bar: 'from-emerald-500 to-teal-400', hex: '#10b981', dot: 'bg-emerald-400' },
    { bar: 'from-sky-500 to-blue-400', hex: '#0ea5e9', dot: 'bg-sky-400' },
    { bar: 'from-indigo-500 to-purple-400', hex: '#6366f1', dot: 'bg-indigo-400' },
    { bar: 'from-amber-500 to-orange-400', hex: '#f59e0b', dot: 'bg-amber-400' },
    { bar: 'from-rose-500 to-pink-400', hex: '#f43f5e', dot: 'bg-rose-400' },
    { bar: 'from-violet-500 to-fuchsia-400', hex: '#8b5cf6', dot: 'bg-violet-400' },
    { bar: 'from-teal-500 to-cyan-400', hex: '#14b8a6', dot: 'bg-teal-400' },
  ];

  // Calculate SVG Donut Arcs
  const radius = 64;
  const strokeWidth = 18;
  const circumference = 2 * Math.PI * radius;

  let cumulativeOffset = 0;
  const donutSegments = entries.map(([sector, val], idx) => {
    const pct = val / total;
    const strokeDasharray = `${pct * circumference} ${circumference}`;
    const strokeDashoffset = -cumulativeOffset * circumference;
    cumulativeOffset += pct;
    const color = colorPalette[idx % colorPalette.length];
    return {
      sector,
      val,
      pct: pct * 100,
      strokeDasharray,
      strokeDashoffset,
      color,
    };
  });

  const hasHighConcentration = entries.some(([, val]) => (val / total) * 100 > 40.0);

  return (
    <div className="glass-panel rounded-3xl p-6 relative overflow-hidden space-y-5">
      {/* Background glow */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-blue-500/5 blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-white/[0.08] relative z-10">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
            <PieChart className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-extrabold tracking-tight text-white uppercase">
              Sector Exposure &amp; Concentration Risk Budgeting
            </h3>
            <p className="text-[11px] text-slate-400">
              Point-in-time sector weight constraints ensuring balanced alpha capture
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5 text-[11px] font-mono">
          <span className="px-2.5 py-1 rounded-lg bg-[#070a14] border border-white/[0.08] text-slate-300">
            Guideline Cap: <strong className="text-sky-300">25%</strong>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-300">
            Hard Stop: <strong className="text-rose-400 font-bold">40%</strong>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center relative z-10">
        {/* Left: Interactive Donut Chart with Center Readout */}
        <div className="lg:col-span-4 flex flex-col items-center justify-center p-2">
          <div className="relative w-44 h-44 flex items-center justify-center select-none">
            <svg viewBox="0 0 170 170" className="w-full h-full -rotate-90">
              {/* Background circle track */}
              <circle
                cx="85"
                cy="85"
                r={radius}
                fill="none"
                stroke="rgba(255, 255, 255, 0.05)"
                strokeWidth={strokeWidth}
              />

              {/* Segments */}
              {donutSegments.map((seg) => {
                const isHovered = hoveredSector === seg.sector;
                return (
                  <circle
                    key={seg.sector}
                    cx="85"
                    cy="85"
                    r={radius}
                    fill="none"
                    stroke={seg.color.hex}
                    strokeWidth={isHovered ? strokeWidth + 4 : strokeWidth}
                    strokeDasharray={seg.strokeDasharray}
                    strokeDashoffset={seg.strokeDashoffset}
                    className="transition-all duration-300 cursor-pointer"
                    style={{
                      filter: isHovered ? `drop-shadow(0 0 10px ${seg.color.hex})` : 'none',
                      opacity: hoveredSector && !isHovered ? 0.35 : 1,
                    }}
                    onMouseEnter={() => setHoveredSector(seg.sector)}
                    onMouseLeave={() => setHoveredSector(null)}
                  />
                );
              })}
            </svg>

            {/* Donut Center Info */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none px-3">
              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider truncate max-w-[110px]">
                {hoveredSector ? hoveredSector.replace(/_/g, ' ') : 'Universe'}
              </span>
              <span className="text-2xl font-black font-mono text-white tracking-tight">
                {hoveredSector
                  ? `${donutSegments.find((s) => s.sector === hoveredSector)?.pct.toFixed(1)}%`
                  : `${entries.length} Sectors`}
              </span>
              <span className={`text-[9px] font-mono font-bold mt-0.5 px-1.5 py-0.2 rounded ${
                hasHighConcentration
                  ? 'bg-amber-500/20 text-amber-300'
                  : 'bg-emerald-500/20 text-emerald-300'
              }`}>
                {hoveredSector ? 'ACTIVE ALLOC' : hasHighConcentration ? 'TILT WARNING' : 'HEALTHY SPREAD'}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Sector Progress Cards (Clean auto-filling grid) */}
        <div className={`lg:col-span-8 grid gap-3.5 ${entries.length <= 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1 sm:grid-cols-2'}`}>
          {entries.map(([sector, val], idx) => {
            const pct = (val / total) * 100;
            const isWarning = pct > 25.0 && pct <= 40.0;
            const isDanger = pct > 40.0;
            const style = colorPalette[idx % colorPalette.length];
            const isHovered = hoveredSector === sector;

            return (
              <div
                key={sector}
                onMouseEnter={() => setHoveredSector(sector)}
                onMouseLeave={() => setHoveredSector(null)}
                className={`p-4 rounded-2xl bg-[#070a14] border transition-all duration-200 cursor-pointer ${
                  isHovered
                    ? 'border-sky-400/60 shadow-[0_0_15px_rgba(56,189,248,0.25)] bg-[#0c1022]'
                    : 'border-white/[0.06] hover:border-white/[0.12]'
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-2">
                  <div className="flex items-center space-x-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${style.dot} shadow-sm`} />
                    <span className="text-slate-200 font-bold capitalize truncate max-w-[140px]">
                      {sector.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-black text-white text-sm">{pct.toFixed(1)}%</span>
                    {isDanger ? (
                      <span className="text-[10px] bg-rose-500/20 text-rose-300 font-mono font-bold px-2 py-0.5 rounded-md border border-rose-500/30 flex items-center">
                        <ShieldAlert className="w-3 h-3 mr-1" /> &gt;40% Cap
                      </span>
                    ) : isWarning ? (
                      <span className="text-[10px] bg-amber-500/20 text-amber-300 font-mono font-bold px-2 py-0.5 rounded-md border border-amber-500/30">
                        &gt;25% Tilt
                      </span>
                    ) : (
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 font-mono font-bold px-2 py-0.5 rounded-md border border-emerald-500/20">
                        Within Cap
                      </span>
                    )}
                  </div>
                </div>

                {/* Progress track with clear guideline ticks */}
                <div className="relative w-full h-2.5 bg-[#04060c] rounded-full overflow-hidden border border-white/[0.06] mt-2">
                  {/* 25% guideline marker */}
                  <div
                    className="absolute top-0 bottom-0 left-1/4 w-[1px] bg-sky-400/60 z-10"
                    title="25% Recommended Cap"
                  />
                  {/* 40% hard limit marker */}
                  <div
                    className="absolute top-0 bottom-0 left-[40%] w-[1.5px] bg-rose-500/80 z-10"
                    title="40% Hard Stop"
                  />
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${style.bar} transition-all duration-500 ease-out`}
                    style={{ width: `${Math.min(100, pct)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default SectorAllocation;
