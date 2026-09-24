import React from 'react';

interface FactorDialsProps {
  compositeScore: number;
  qualityScore: number;
  valuationScore: number;
  riskScore: number;
  sentimentOverlay: number;
}

export const FactorDials: React.FC<FactorDialsProps> = ({
  compositeScore,
  qualityScore,
  valuationScore,
  riskScore,
  sentimentOverlay,
}) => {
  const bars = [
    { label: 'Quality (40%)', score: qualityScore, max: 100, gradient: 'from-emerald-500 to-teal-300', text: 'text-emerald-400' },
    { label: 'Valuation (30%)', score: valuationScore, max: 100, gradient: 'from-indigo-500 to-purple-400', text: 'text-purple-400' },
    { label: 'Low Risk (30%)', score: riskScore, max: 100, gradient: 'from-blue-500 to-cyan-300', text: 'text-cyan-400' },
  ];

  return (
    <div className="space-y-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
          Composite Score
        </span>
        <div className="flex items-baseline space-x-1">
          <span className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 font-mono">
            {compositeScore.toFixed(1)}
          </span>
          <span className="text-[10px] text-slate-500 font-mono">/ 100</span>
        </div>
      </div>

      <div className="space-y-2.5">
        {bars.map((b) => {
          const pct = Math.min(100, Math.max(0, (b.score / b.max) * 100));
          return (
            <div key={b.label}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400 text-[11px] font-medium">{b.label}</span>
                <span className={`font-bold font-mono text-[11px] ${b.text}`}>{b.score.toFixed(1)}</span>
              </div>
              <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${b.gradient} transition-all duration-500 shadow-sm`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-800/80">
        <span className="text-slate-400 text-[11px]">Sentiment Overlay:</span>
        <span
          className={`font-bold font-mono px-2 py-0.5 rounded text-[11px] ${
            sentimentOverlay > 0
              ? 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
              : sentimentOverlay < 0
              ? 'bg-rose-500/10 text-rose-300 border border-rose-500/30'
              : 'text-slate-400'
          }`}
        >
          {sentimentOverlay > 0 ? `+${sentimentOverlay.toFixed(1)}` : sentimentOverlay.toFixed(1)} pts
        </span>
      </div>
    </div>
  );
};
