import React, { useMemo } from 'react';
import { Shield, Sparkles } from 'lucide-react';

interface MarketRegimeArcGaugeProps {
  score?: number; // 0 - 100
  regime?: string;
  vix?: number;
}

export const MarketRegimeArcGauge: React.FC<MarketRegimeArcGaugeProps> = ({
  score = 66,
  regime = 'NEUTRAL',
  vix = 12.69,
}) => {
  // Generate radiating tick marks for 180-degree semi-circle
  const ticksCount = 37;
  const activeTicks = Math.round((score / 100) * ticksCount);

  // Needle angle: spans from -90 degrees (score 0) to +90 degrees (score 100)
  const needleAngle = -90 + (score / 100) * 180;

  const cx = 130;
  const cy = 118;
  const rInner = 74;
  const rOuter = 94;

  const ticks = useMemo(() => {
    const arr = [];
    for (let i = 0; i < ticksCount; i++) {
      const angle = Math.PI + (i / (ticksCount - 1)) * Math.PI;
      const x1 = cx + rInner * Math.cos(angle);
      const y1 = cy + rInner * Math.sin(angle);
      const x2 = cx + rOuter * Math.cos(angle);
      const y2 = cy + rOuter * Math.sin(angle);

      const isActive = i <= activeTicks;
      const ratio = i / (ticksCount - 1);

      // Color scheme along the arc
      let colorClass = '#0ea5e9';
      if (ratio < 0.35) colorClass = '#10b981'; // Low Vol (Emerald)
      else if (ratio < 0.70) colorClass = '#38bdf8'; // Neutral (Sky)
      else if (ratio < 0.85) colorClass = '#f59e0b'; // Elevated (Amber)
      else colorClass = '#f43f5e'; // Volatile (Rose)

      arr.push({ id: i, x1, y1, x2, y2, isActive, colorClass });
    }
    return arr;
  }, [ticksCount, activeTicks]);

  // Determine regime guidance
  const regimeInfo = useMemo(() => {
    if (vix < 13) {
      return {
        label: 'Low Volatility Bull',
        color: 'text-emerald-400',
        badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
        guidance: 'Favorable for high-beta momentum and multi-cap quality compounding.',
      };
    } else if (vix < 17) {
      return {
        label: 'Normal Dispersion Regime',
        color: 'text-sky-400',
        badge: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
        guidance: 'Stock picking alpha dominates. Maintain balanced 25% sector caps.',
      };
    } else if (vix < 22) {
      return {
        label: 'Elevated Risk / Consolidation',
        color: 'text-amber-400',
        badge: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
        guidance: 'Exercise dip discipline. Prioritize zero-debt, high FCF generators.',
      };
    } else {
      return {
        label: 'High Volatility Markdown',
        color: 'text-rose-400',
        badge: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
        guidance: 'Defensive cash allocation active. Protect capital and await stabilization.',
      };
    }
  }, [vix]);

  return (
    <div className="glass-panel p-6 rounded-3xl relative overflow-hidden flex flex-col justify-between space-y-4">
      {/* Background ambient corner glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between relative z-10">
        <div className="flex items-center space-x-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-sky-400 animate-ping" />
          <h3 className="text-sm font-extrabold text-white tracking-wide flex items-center">
            NSE Market Regime &amp; Volatility Arc
          </h3>
        </div>
        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border uppercase ${regimeInfo.badge}`}>
          {regime}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 items-center relative z-10">
        {/* Left: Metrics breakdown */}
        <div className="space-y-2.5">
          <div className="p-2.5 rounded-xl bg-[#070a13] border border-white/[0.06] flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              <span className="text-slate-300 font-medium">Momentum Breadth</span>
            </div>
            <span className="font-mono font-extrabold text-emerald-400">76.4%</span>
          </div>

          <div className="p-2.5 rounded-xl bg-[#070a13] border border-white/[0.06] flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.8)]" />
              <span className="text-slate-300 font-medium">Quality Factor Spread</span>
            </div>
            <span className="font-mono font-extrabold text-sky-400">84.2%</span>
          </div>

          <div className="p-2.5 rounded-xl bg-[#070a13] border border-white/[0.06] flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]" />
              <span className="text-slate-300 font-medium">Liquidity Buffer</span>
            </div>
            <span className="font-mono font-extrabold text-indigo-400">62.0%</span>
          </div>

          <div className="p-2.5 rounded-xl bg-[#070a13] border border-white/[0.06] flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]" />
              <span className="text-slate-300 font-medium">India VIX Level</span>
            </div>
            <span className="font-mono font-extrabold text-amber-400">{vix.toFixed(2)}</span>
          </div>
        </div>

        {/* Right: Clean Speedometer Arc with Non-Overlapping Layout */}
        <div className="flex flex-col items-center justify-center relative">
          <svg
            viewBox="0 0 260 140"
            className="w-full max-w-[240px] drop-shadow-[0_0_20px_rgba(37,99,235,0.25)] select-none"
          >
            <defs>
              <linearGradient id="needleGrad" x1="0%" y1="100%" x2="0%" y2="0%">
                <stop offset="0%" stopColor="#0284c7" />
                <stop offset="100%" stopColor="#38bdf8" />
              </linearGradient>
            </defs>

            {/* Glowing ticks along the arc */}
            {ticks.map((t) => (
              <line
                key={t.id}
                x1={t.x1}
                y1={t.y1}
                x2={t.x2}
                y2={t.y2}
                stroke={t.isActive ? t.colorClass : 'rgba(255, 255, 255, 0.14)'}
                strokeWidth={t.isActive ? '2.8' : '1.5'}
                strokeLinecap="round"
                className="transition-all duration-300"
              />
            ))}

            {/* Arc boundary baseline track */}
            <path
              d="M 48 118 A 82 82 0 0 1 212 118"
              fill="none"
              stroke="rgba(255, 255, 255, 0.08)"
              strokeWidth="1.5"
              strokeDasharray="2 3"
            />

            {/* Needle Pivot Base */}
            <circle cx={cx} cy={cy} r="8" fill="#080c16" stroke="#38bdf8" strokeWidth="2" />
            <circle cx={cx} cy={cy} r="3" fill="#38bdf8" />

            {/* Rotating Needle with smooth CSS transition */}
            <g
              style={{
                transform: `rotate(${needleAngle}deg)`,
                transformOrigin: `${cx}px ${cy}px`,
                transition: 'transform 1s cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            >
              <line
                x1={cx}
                y1={cy}
                x2={cx}
                y2={cy - 68}
                stroke="url(#needleGrad)"
                strokeWidth="2.75"
                strokeLinecap="round"
              />
              <circle cx={cx} cy={cy - 66} r="2.5" fill="#ffffff" />
            </g>
          </svg>

          {/* Clean Score Readout with zero needle collision */}
          <div className="flex flex-col items-center justify-center text-center -mt-2">
            <span className="text-3xl font-black font-mono text-white tracking-tight drop-shadow-[0_2px_12px_rgba(56,189,248,0.5)]">
              {score.toFixed(1)}
            </span>
            <div className="flex items-center space-x-1.5 mt-0.5">
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              <span className={`text-xs font-bold font-mono tracking-wide ${regimeInfo.color}`}>
                {regimeInfo.label}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Guidance Pill with wrapping safeguard */}
      <div className="pt-3 border-t border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-400 relative z-10">
        <div className="flex items-center text-[11px] text-slate-300 min-w-0">
          <Shield className="w-3.5 h-3.5 text-emerald-400 mr-1.5 shrink-0" />
          <span className="truncate">{regimeInfo.guidance}</span>
        </div>
        <div className="shrink-0 self-end sm:self-auto">
          <span className="text-[10px] text-sky-400 font-mono font-bold px-2.5 py-0.5 rounded-full bg-sky-500/10 border border-sky-500/20 whitespace-nowrap">
            VIX PERCENTILE: 22%
          </span>
        </div>
      </div>
    </div>
  );
};

export default MarketRegimeArcGauge;
