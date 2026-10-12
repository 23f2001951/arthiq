import React, { useMemo, useState } from 'react';
import { ArrowUpRight, BarChart3 } from 'lucide-react';
import { StockRecommendationItem } from '../types/api';

type FactorKey = 'composite_score' | 'quality_score' | 'valuation_score' | 'risk_score';

interface PulseViewProps {
  recommendations: StockRecommendationItem[];
  asof: string;
}

const FACTORS: { id: FactorKey; label: string; description: string }[] = [
  { id: 'composite_score', label: 'Composite', description: 'Combined recommendation score' },
  { id: 'quality_score', label: 'Quality', description: 'Business quality score' },
  { id: 'valuation_score', label: 'Valuation', description: 'Valuation score' },
  { id: 'risk_score', label: 'Risk', description: 'Risk assessment score' },
];

export const PulseView: React.FC<PulseViewProps> = ({ recommendations, asof }) => {
  const [factor, setFactor] = useState<FactorKey>('composite_score');
  const activeFactor = FACTORS.find((item) => item.id === factor) || FACTORS[0];
  const leaders = useMemo(
    () => [...recommendations].sort((a, b) => b[factor] - a[factor]).slice(0, 8),
    [recommendations, factor],
  );

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-winsor-300 font-semibold">Current recommendation set</p>
          <h2 className="mt-1 text-xl font-semibold text-white">Factor leaders</h2>
          <p className="mt-1 text-xs text-slate-400">Ranked from actual recommendation scores · as of {asof}</p>
        </div>
        <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Choose ranking factor">
          {FACTORS.map((item) => (
            <button key={item.id} role="tab" aria-selected={factor === item.id} onClick={() => setFactor(item.id)} className={`px-3 py-2 rounded-xl border text-xs font-medium transition-colors ${factor === item.id ? 'bg-winsor-800 text-white border-winsor-500/40' : 'bg-white/[0.02] text-slate-400 border-white/[0.08] hover:text-white'}`}>
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {leaders.length === 0 ? (
        <div className="glass-card min-h-48 rounded-2xl p-8 flex flex-col items-center justify-center text-center">
          <BarChart3 className="w-6 h-6 text-slate-500 mb-3" />
          <h3 className="text-sm font-semibold text-white">No recommendation scores available</h3>
          <p className="mt-1 max-w-md text-xs leading-relaxed text-slate-400">Run or select a point-in-time recommendation set to see factor leaders. This view does not fill gaps with sample stocks.</p>
        </div>
      ) : (
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-white/[0.08] flex items-center justify-between gap-3">
            <span className="text-xs font-semibold text-slate-200">{activeFactor.description}</span>
            <span className="text-[10px] text-slate-500">{leaders.length} of {recommendations.length} names</span>
          </div>
          <div className="divide-y divide-white/[0.06]">
            {leaders.map((item, index) => (
              <div key={item.symbol} className="grid grid-cols-[2rem_minmax(0,1fr)_minmax(6rem,2fr)_4rem] items-center gap-3 px-4 py-3">
                <span className="font-mono text-xs text-slate-500">{String(index + 1).padStart(2, '0')}</span>
                <div className="min-w-0">
                  <div className="font-mono text-sm font-semibold text-white">{item.symbol}</div>
                  <div className="text-[10px] text-slate-500 truncate">{item.sector.replace(/_/g, ' ')}</div>
                </div>
                <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                  <div className="h-full rounded-full bg-winsor-400 transition-[width] duration-500" style={{ width: `${Math.max(0, Math.min(100, item[factor]))}%` }} />
                </div>
                <span className="text-right font-mono text-sm font-semibold text-winsor-200">{item[factor].toFixed(1)}</span>
              </div>
            ))}
          </div>
          <p className="px-4 py-3 text-[10px] leading-relaxed text-slate-500 border-t border-white/[0.06] flex items-start gap-1.5"><ArrowUpRight className="w-3 h-3 mt-0.5 shrink-0" /> A factor ranking is a model view, not a price trend or a guaranteed return.</p>
        </div>
      )}
    </section>
  );
};
