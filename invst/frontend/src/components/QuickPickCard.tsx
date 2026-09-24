import React, { useState } from 'react';
import {
  Sparkles,
  Building2,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  TrendingUp,
  Cpu,
  CheckCircle2,
} from 'lucide-react';
import { QuickPickItem } from '../types/api';
import { FactorDials } from './FactorDials';

interface QuickPickCardProps {
  pick: QuickPickItem;
}

export const QuickPickCard: React.FC<QuickPickCardProps> = ({ pick }) => {
  const [expanded, setExpanded] = useState(false);

  const formatPct = (val?: number | null) => (val !== undefined && val !== null ? `${val.toFixed(2)}%` : '—');
  const formatNum = (val?: number | null) => (val !== undefined && val !== null ? val.toFixed(2) : '—');

  const probPct = Math.round((pick.p_outperform ?? 0.5) * 100);
  const expAlpha = pick.expected_alpha_pct ?? 0.0;
  const arthScore = pick.arth_score ?? Math.round(pick.composite_score * 100);
  const agreement = Math.round((pick.signal_agreement ?? 1.0) * 100);
  const convictionTier = pick.conviction_tier ?? 'HIGH CONVICTION ALPHA';

  return (
    <div className="glass-card rounded-3xl p-6 relative overflow-hidden border border-white/[0.08] hover:border-winsor-500/40 transition-all duration-300 shadow-2xl group">
      {/* Top Accent Gradient Bar */}
      <div className="absolute top-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-winsor-600 via-sky-400 to-emerald-400" />
      <div className="absolute inset-0 bg-dot-grid opacity-15 pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 relative z-10">
        <div className="flex items-center space-x-3.5">
          {/* Rank Badge */}
          <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-winsor-700 via-winsor-600 to-sky-400 text-white font-black text-lg shadow-lg shadow-winsor-500/25 font-mono shrink-0">
            #{pick.rank}
          </div>

          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-2xl font-black text-white tracking-tight font-mono group-hover:text-sky-300 transition-colors">
                {pick.symbol}
              </h3>
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border flex items-center gap-1 ${
                probPct >= 70
                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40'
                  : probPct >= 55
                  ? 'bg-sky-950/80 text-sky-300 border-sky-500/40'
                  : 'bg-amber-950/80 text-amber-300 border-amber-500/40'
              }`}>
                <Sparkles className="w-3 h-3 text-sky-400" />
                {convictionTier}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#0e1322] text-sky-300 border border-sky-500/30">
                ArthScore: {arthScore.toFixed(1)}
              </span>
            </div>
            <div className="flex items-center text-xs text-slate-400 mt-1 space-x-2">
              <span className="flex items-center">
                <Building2 className="w-3.5 h-3.5 mr-1 text-slate-500" />
                <span className="capitalize">{pick.sector.replace(/_/g, ' ')}</span>
              </span>
              {pick.latest_close && (
                <>
                  <span className="text-slate-600">•</span>
                  <span className="text-white font-mono font-bold">
                    LTP: ₹{pick.latest_close.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Suggested Allocation Badge */}
        <div className="sm:text-right bg-[#090b14] px-4 py-2.5 rounded-2xl border border-white/[0.06] shrink-0 flex sm:flex-col items-center sm:items-end justify-between">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Suggested Sizing
          </span>
          <div className="flex items-baseline space-x-1 sm:mt-0.5">
            <span className="text-2xl font-black font-mono text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-teal-300 to-emerald-400">
              {(pick.suggested_weight * 100).toFixed(0)}%
            </span>
            <span className="text-xs text-slate-400 font-medium">of cash</span>
          </div>
        </div>
      </div>

      {/* Predictive ML Engine Strip */}
      <div className="mt-4 p-3.5 rounded-2xl bg-gradient-to-r from-[#090d1a] to-[#0a1120] border border-sky-500/20 relative z-10 shadow-inner">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-sky-500/10 border border-sky-400/20 flex items-center justify-center shrink-0">
              <Cpu className="w-4 h-4 text-sky-400" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-bold text-white font-mono">
                  Calibrated P(Alpha &gt; 0):
                </span>
                <span className={`text-sm font-black font-mono ${
                  probPct >= 70 ? 'text-emerald-400' : 'text-sky-300'
                }`}>
                  {probPct}%
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  (Brier Calibrated)
                </span>
              </div>
              <div className="w-44 h-1.5 bg-[#080a12] rounded-full overflow-hidden mt-1 border border-white/[0.08]">
                <div
                  className="h-full bg-gradient-to-r from-sky-500 to-emerald-400 transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, probPct))}%` }}
                />
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
            <div className="px-2.5 py-1 rounded-xl bg-[#080c18] border border-white/[0.06] flex items-center space-x-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-400">Exp Alpha:</span>
              <span className="font-bold text-emerald-300">{expAlpha >= 0 ? `+${expAlpha.toFixed(1)}%` : `${expAlpha.toFixed(1)}%`}</span>
            </div>
            <div className="px-2.5 py-1 rounded-xl bg-[#080c18] border border-white/[0.06] flex items-center space-x-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-sky-400" />
              <span className="text-slate-400">Signal Agreement:</span>
              <span className="font-bold text-white">{agreement}%</span>
            </div>
          </div>
        </div>

        {/* Multi-Horizon Projections */}
        {pick.multi_horizon_projections && Object.keys(pick.multi_horizon_projections).length > 0 && (
          <div className="mt-2.5 pt-2 border-t border-white/[0.04] flex flex-wrap items-center gap-2 text-[10px] font-mono">
            <span className="text-slate-500 uppercase tracking-wider font-semibold">Horizon Fit:</span>
            {Object.entries(pick.multi_horizon_projections).map(([h, val]) => (
              <span
                key={h}
                className="px-2 py-0.5 rounded-lg bg-[#060912] border border-white/[0.06] text-slate-300"
              >
                <span className="text-slate-500 mr-1">{h}:</span>
                <span className={val >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                  {val >= 0 ? `+${val.toFixed(1)}%` : `${val.toFixed(1)}%`}
                </span>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Narrative Rationale Box */}
      <div className="mt-4 p-4 rounded-2xl bg-[#080a12] border border-white/[0.06] text-xs text-slate-200 leading-relaxed relative z-10">
        <div className="flex items-center space-x-1.5 text-sky-300 font-mono font-bold text-[11px] mb-1.5">
          <Sparkles className="w-3.5 h-3.5 text-sky-400" />
          <span>Arth IQ Investment Thesis</span>
        </div>
        <p className="text-slate-300 font-sans leading-relaxed">{pick.rationale}</p>
      </div>

      {/* Factor Dials & Score Breakdown */}
      <div className="mt-5 pt-4 border-t border-white/[0.06] relative z-10">
        <FactorDials
          compositeScore={pick.composite_score * 100}
          qualityScore={pick.quality_score * 100}
          valuationScore={pick.valuation_score * 100}
          riskScore={pick.risk_score * 100}
          sentimentOverlay={pick.sentiment_overlay_points}
        />
      </div>

      {/* Expandable Fundamental Metrics */}
      <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center justify-between relative z-10">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-slate-400 hover:text-sky-300 font-semibold flex items-center transition-colors cursor-pointer"
        >
          <span>{expanded ? 'Collapse Metrics' : 'Inspect PIT Metrics & Ratios'}</span>
          {expanded ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />}
        </button>

        <div className="text-[11px] font-mono text-slate-400 flex items-center space-x-1">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 mr-1" />
          <span>Point-in-Time Audit Verified</span>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-white/[0.06] grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono relative z-10 animate-fadeIn">
          <div className="p-3 bg-[#080b13] rounded-xl border border-white/[0.04]">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">ROCE</span>
            <span className="text-white font-black text-sm">{formatPct(pick.quality_metrics?.roce)}</span>
          </div>
          <div className="p-3 bg-[#080b13] rounded-xl border border-white/[0.04]">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">ROE</span>
            <span className="text-white font-black text-sm">{formatPct(pick.quality_metrics?.roe)}</span>
          </div>
          <div className="p-3 bg-[#080b13] rounded-xl border border-white/[0.04]">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">P/E Ratio</span>
            <span className="text-white font-black text-sm">{formatNum(pick.valuation_metrics?.pe_ratio)}</span>
          </div>
          <div className="p-3 bg-[#080b13] rounded-xl border border-white/[0.04]">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Debt / Equity</span>
            <span className="text-white font-black text-sm">{formatNum(pick.risk_metrics?.debt_to_equity)}</span>
          </div>
        </div>
      )}
    </div>
  );
};
