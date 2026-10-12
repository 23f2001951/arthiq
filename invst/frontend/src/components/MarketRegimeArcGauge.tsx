import React, { useMemo } from 'react';
import { Activity } from 'lucide-react';

interface MarketRegimeArcGaugeProps {
  regime: string;
  vix: number;
  description: string;
}

export const MarketRegimeArcGauge: React.FC<MarketRegimeArcGaugeProps> = ({ regime, vix, description }) => {
  const ticks = useMemo(() => {
    const count = 31;
    const low = 10;
    const high = 35;
    const active = Math.round(Math.max(0, Math.min(1, (vix - low) / (high - low))) * (count - 1));
    return Array.from({ length: count }, (_, i) => {
      const angle = Math.PI + (i / (count - 1)) * Math.PI;
      const ratio = i / (count - 1);
      const color = ratio < 0.33 ? '#78905a' : ratio < 0.66 ? '#c7ad70' : '#bb7766';
      return {
        id: i,
        x1: 130 + 76 * Math.cos(angle),
        y1: 112 + 76 * Math.sin(angle),
        x2: 130 + 94 * Math.cos(angle),
        y2: 112 + 94 * Math.sin(angle),
        color: i <= active ? color : 'rgba(255,255,255,0.12)',
      };
    });
  }, [vix]);

  return (
    <section className="glass-panel min-h-64 p-6 flex flex-col justify-between" aria-label="Market volatility regime">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Activity className="w-4 h-4 text-winsor-300" />
          <h3 className="text-sm font-semibold text-white">India VIX &amp; Market Regime</h3>
        </div>
        <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold border border-winsor-400/20 bg-winsor-500/10 text-winsor-200">
          {regime.replace(/_/g, ' ')}
        </span>
      </div>

      <div className="flex items-center justify-center py-1">
        <div className="relative w-full max-w-[250px]">
          <svg viewBox="0 0 260 140" className="w-full" role="img" aria-label={`India VIX ${vix.toFixed(2)}`}>
            {ticks.map((tick) => (
              <line key={tick.id} x1={tick.x1} y1={tick.y1} x2={tick.x2} y2={tick.y2} stroke={tick.color} strokeWidth="2.5" strokeLinecap="round" />
            ))}
            <text x="130" y="93" textAnchor="middle" fill="currentColor" className="text-3xl font-semibold font-mono" style={{ color: 'var(--gold)' }}>
              {vix.toFixed(2)}
            </text>
            <text x="130" y="113" textAnchor="middle" fill="currentColor" className="text-[10px] tracking-[0.2em] uppercase text-slate-400">
              INDIA VIX
            </text>
          </svg>
        </div>
      </div>

      <div className="border-t border-white/[0.08] pt-3 flex items-start justify-between gap-4">
        <p className="text-xs leading-relaxed text-slate-400">{description}</p>
        <span className="text-[9px] font-mono uppercase tracking-wider text-emerald-300 shrink-0">Live quote</span>
      </div>
    </section>
  );
};

export default MarketRegimeArcGauge;
