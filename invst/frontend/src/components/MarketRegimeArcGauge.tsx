import React, { useMemo } from 'react';
import { Shield, Sparkles, MoreHorizontal } from 'lucide-react';

interface MarketRegimeArcGaugeProps {
  score?: number; // 0 - 100
  regime?: string;
  vix?: number;
}

export const MarketRegimeArcGauge: React.FC<MarketRegimeArcGaugeProps> = ({
  score = 84,
  regime = 'EXPANSION',
  vix = 12.8,
}) => {
  // Generate radiating tick marks for 180-degree semi-circle
  const ticksCount = 36;
  const activeTicks = Math.round((score / 100) * ticksCount);

  const ticks = useMemo(() => {
    const arr = [];
    const cx = 130;
    const cy = 130;
    const rInner = 88;
    const rOuter = 108;

    for (let i = 0; i < ticksCount; i++) {
      // Angle spans 180 degrees from Math.PI to 2*Math.PI (bottom is flat, arc arches upwards)
      const angle = Math.PI + (i / (ticksCount - 1)) * Math.PI;
      const x1 = cx + rInner * Math.cos(angle);
      const y1 = cy + rInner * Math.sin(angle);
      const x2 = cx + rOuter * Math.cos(angle);
      const y2 = cy + rOuter * Math.sin(angle);

      const isActive = i <= activeTicks;
      arr.push({ id: i, x1, y1, x2, y2, isActive });
    }
    return arr;
  }, [ticksCount, activeTicks]);

  return (
    <div className="glass-card p-6 relative overflow-hidden flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-winsor-500 animate-ping" />
          <h3 className="text-sm font-semibold text-slate-200 tracking-wide">
            Market Regime & Sentiment
          </h3>
        </div>
        <button className="text-slate-500 hover:text-slate-300 transition-colors">
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-center">
        {/* Left metrics breakdown list */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-winsor-400 shadow-[0_0_8px_rgba(56,189,248,0.8)]" />
              <span className="text-slate-300 font-medium">Momentum Breadth</span>
            </div>
            <span className="font-mono font-bold text-slate-100">76%</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              <span className="text-slate-300 font-medium">Quality Factor Spread</span>
            </div>
            <span className="font-mono font-bold text-slate-100">84%</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]" />
              <span className="text-slate-300 font-medium">Liquidity Buffer</span>
            </div>
            <span className="font-mono font-bold text-slate-100">62%</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]" />
              <span className="text-slate-300 font-medium">India VIX Volatility</span>
            </div>
            <span className="font-mono font-bold text-slate-100">{vix}</span>
          </div>
        </div>

        {/* Right Arc Gauge */}
        <div className="relative flex flex-col items-center justify-center">
          <svg
            viewBox="0 0 260 145"
            className="w-full max-w-[240px] drop-shadow-[0_0_20px_rgba(37,99,235,0.25)]"
          >
            <defs>
              <linearGradient id="activeTickGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#2563eb" />
                <stop offset="50%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#60a5fa" />
              </linearGradient>
            </defs>

            {/* Glowing ticks */}
            {ticks.map((t) => (
              <line
                key={t.id}
                x1={t.x1}
                y1={t.y1}
                x2={t.x2}
                y2={t.y2}
                stroke={t.isActive ? 'url(#activeTickGrad)' : 'rgba(255, 255, 255, 0.12)'}
                strokeWidth={t.isActive ? '3' : '2'}
                strokeLinecap="round"
                className="transition-all duration-300"
              />
            ))}
          </svg>

          {/* Center value readout */}
          <div className="absolute bottom-1 flex flex-col items-center justify-center text-center">
            <span className="text-2xl sm:text-3xl font-extrabold font-mono text-white tracking-tight drop-shadow-[0_2px_12px_rgba(56,189,248,0.4)]">
              {score}.4
            </span>
            <div className="flex items-center space-x-1 mt-0.5">
              <Sparkles className="w-3 h-3 text-winsor-400" />
              <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-widest">
                {regime}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Pill */}
      <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center text-[11px]">
          <Shield className="w-3.5 h-3.5 text-emerald-400 mr-1.5" />
          Quant Risk Envelope: Low Drawdown Prob
        </span>
        <span className="text-[10px] text-winsor-400 font-mono">CONFIDENCE: 94.2%</span>
      </div>
    </div>
  );
};
