import React from 'react';
import { PieChart, ShieldAlert } from 'lucide-react';

interface SectorAllocationProps {
  sectors: Record<string, number>;
}

export const SectorAllocation: React.FC<SectorAllocationProps> = ({ sectors }) => {
  const entries = Object.entries(sectors).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((acc, [, val]) => acc + val, 0) || 1;

  const colorPalette = [
    { bar: 'from-emerald-500 to-teal-400', dot: 'bg-emerald-400' },
    { bar: 'from-cyan-500 to-blue-400', dot: 'bg-cyan-400' },
    { bar: 'from-indigo-500 to-purple-400', dot: 'bg-purple-400' },
    { bar: 'from-amber-500 to-orange-400', dot: 'bg-amber-400' },
    { bar: 'from-rose-500 to-pink-400', dot: 'bg-rose-400' },
    { bar: 'from-violet-500 to-fuchsia-400', dot: 'bg-violet-400' },
    { bar: 'from-sky-500 to-indigo-400', dot: 'bg-sky-400' },
  ];

  return (
    <div className="glass-card rounded-2xl p-6 border border-slate-800 shadow-xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div className="flex items-center space-x-2">
          <PieChart className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-black uppercase tracking-wider text-white">
            Sector Exposure & Risk Budgeting
          </h3>
        </div>
        <div className="flex items-center space-x-3 text-[11px] font-mono">
          <span className="text-slate-400">Guide Cap: <strong className="text-slate-200">25%</strong></span>
          <span className="text-slate-400">Hard Cap: <strong className="text-rose-400">40%</strong></span>
        </div>
      </div>

      {/* Multi-segment stack bar */}
      <div className="w-full h-3.5 bg-slate-950 rounded-full flex overflow-hidden border border-slate-800 shadow-inner">
        {entries.map(([sector, val], idx) => {
          const pct = (val / total) * 100;
          const style = colorPalette[idx % colorPalette.length];
          return (
            <div
              key={sector}
              className={`h-full bg-gradient-to-r ${style.bar} transition-all duration-500 hover:brightness-125 cursor-pointer`}
              style={{ width: `${pct}%` }}
              title={`${sector.replace(/_/g, ' ')}: ${pct.toFixed(1)}%`}
            />
          );
        })}
      </div>

      {/* Detailed Horizontal Bars with 25% and 40% Marker Reference Lines */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {entries.map(([sector, val], idx) => {
          const pct = (val / total) * 100;
          const isWarning = pct > 25.0;
          const isDanger = pct > 40.0;
          const style = colorPalette[idx % colorPalette.length];

          return (
            <div
              key={sector}
              className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center justify-between text-xs mb-2">
                <div className="flex items-center space-x-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${style.dot} shadow-sm`} />
                  <span className="text-slate-200 font-bold capitalize">
                    {sector.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="font-extrabold text-white font-mono">{pct.toFixed(1)}%</span>
                  {isDanger ? (
                    <span className="text-[10px] bg-rose-500/20 text-rose-300 font-bold px-1.5 py-0.5 rounded border border-rose-500/30 flex items-center">
                      <ShieldAlert className="w-2.5 h-2.5 mr-0.5" /> &gt;40% Cap
                    </span>
                  ) : isWarning ? (
                    <span className="text-[10px] bg-amber-500/20 text-amber-300 font-bold px-1.5 py-0.5 rounded border border-amber-500/30">
                      &gt;25% Tilt
                    </span>
                  ) : null}
                </div>
              </div>

              {/* Progress track with 25% and 40% guide marks */}
              <div className="relative w-full h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                {/* 25% tick */}
                <div className="absolute top-0 bottom-0 left-1/4 w-[1px] bg-slate-700 z-10" />
                {/* 40% tick */}
                <div className="absolute top-0 bottom-0 left-[40%] w-[1px] bg-rose-800/80 z-10" />
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${style.bar} transition-all duration-500`}
                  style={{ width: `${Math.min(100, pct)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
