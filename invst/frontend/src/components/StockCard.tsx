import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Sparkles, Building2, ShieldCheck } from 'lucide-react';
import { StockRecommendationItem } from '../types/api';
import { FactorDials } from './FactorDials';

interface StockCardProps {
  stock: StockRecommendationItem;
  rank: number;
}

export const StockCard: React.FC<StockCardProps> = ({ stock, rank }) => {
  const [expanded, setExpanded] = useState(false);

  const formatPct = (val?: number | null) => (val !== undefined && val !== null ? `${val.toFixed(2)}%` : '—');
  const formatNum = (val?: number | null) => (val !== undefined && val !== null ? val.toFixed(2) : '—');

  return (
    <div className="glass-card rounded-3xl p-6 hover:border-winsor-500/40 transition-all duration-300 shadow-xl group relative overflow-hidden">
      <div className="absolute inset-0 bg-dot-grid opacity-10 pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 relative z-10">
        <div className="flex items-center space-x-3.5">
          <div className="flex items-center justify-center w-11 h-11 rounded-2xl bg-[#0e121e] border border-sky-500/30 text-sky-300 font-black text-sm shadow-inner font-mono shrink-0 group-hover:border-sky-400 group-hover:text-sky-200 transition-colors">
            #{rank}
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <h3 className="text-xl font-black text-white tracking-tight group-hover:text-sky-300 transition-colors font-mono">
                {stock.symbol}
              </h3>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
                {stock.action}
              </span>
            </div>
            <div className="flex items-center text-xs text-slate-400 mt-1">
              <Building2 className="w-3.5 h-3.5 mr-1 text-slate-500" />
              <span className="capitalize">{stock.sector.replace(/_/g, ' ')}</span>
            </div>
          </div>
        </div>

        {/* Right side: Sparkline & Target Weight */}
        <div className="flex items-center space-x-4 self-end sm:self-auto">
          <div className="hidden sm:block text-right">
            <span className="text-[10px] uppercase tracking-wider text-slate-500 block mb-0.5 font-mono">
              Sentiment Overlay
            </span>
            <span className="font-mono text-sm font-bold text-slate-200">
              {stock.sentiment_overlay_points > 0 ? '+' : ''}{stock.sentiment_overlay_points.toFixed(1)} pts
            </span>
          </div>

          <div className="text-right bg-[#090b14] px-3.5 py-1.5 rounded-2xl border border-white/[0.06]">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-bold">
              Target Weight
            </span>
            <span className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-teal-300 to-emerald-400 font-mono">
              {(stock.target_weight * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Narrative "Why Arth IQ Ranks It" */}
      <div className="mt-4 p-4 rounded-2xl bg-[#080a12] border border-white/[0.04] text-xs text-slate-300 relative z-10">
        <div className="flex items-center space-x-1.5 text-sky-300 font-mono font-bold text-[11px] mb-1">
          <Sparkles className="w-3.5 h-3.5 text-sky-400" />
          <span>Arth IQ Quantitative Rationale</span>
        </div>
        <p className="leading-relaxed font-sans">{stock.rationale}</p>
      </div>

      {/* Factor Dials */}
      <div className="mt-4 pt-3 border-t border-white/[0.06] relative z-10">
        <FactorDials
          compositeScore={stock.composite_score}
          qualityScore={stock.quality_score}
          valuationScore={stock.valuation_score}
          riskScore={stock.risk_score}
          sentimentOverlay={stock.sentiment_overlay_points}
        />
      </div>

      {/* Expand / Collapse Ratios */}
      <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center justify-between relative z-10">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-slate-400 hover:text-sky-300 font-semibold flex items-center transition-colors cursor-pointer"
        >
          <span>{expanded ? 'Hide Factor Ratios' : 'Inspect Factor Ratios & Inputs'}</span>
          {expanded ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />}
        </button>

        <div className="text-[11px] font-mono text-slate-400 flex items-center space-x-1">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 mr-1" />
          <span>Point-in-Time Validated</span>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-white/[0.06] grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono relative z-10 animate-fadeIn">
          <div className="p-3 bg-[#080b13] rounded-xl border border-white/[0.04]">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">ROCE</span>
            <span className="text-white font-black text-sm">{formatPct(stock.quality_metrics?.roce)}</span>
          </div>
          <div className="p-3 bg-[#080b13] rounded-xl border border-white/[0.04]">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">ROE</span>
            <span className="text-white font-black text-sm">{formatPct(stock.quality_metrics?.roe)}</span>
          </div>
          <div className="p-3 bg-[#080b13] rounded-xl border border-white/[0.04]">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">P/E Ratio</span>
            <span className="text-white font-black text-sm">{formatNum(stock.valuation_metrics?.pe_ratio)}</span>
          </div>
          <div className="p-3 bg-[#080b13] rounded-xl border border-white/[0.04]">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Debt / Equity</span>
            <span className="text-white font-black text-sm">{formatNum(stock.risk_metrics?.debt_to_equity)}</span>
          </div>
        </div>
      )}
    </div>
  );
};
