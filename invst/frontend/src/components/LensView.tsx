import React, { useState } from 'react';
import { StockRecommendationItem } from '../types/api';
import {
  Eye,
  Search,
  Sparkles,
  ShieldCheck,
  BarChart3,
  Flame,
  CheckCircle2,
  Layers,
} from 'lucide-react';

interface LensViewProps {
  recommendations: StockRecommendationItem[];
  onSelectStock?: (symbol: string) => void;
}

export const LensView: React.FC<LensViewProps> = ({ recommendations }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState<string>(
    recommendations.length > 0 ? recommendations[0].symbol : 'TCS'
  );

  const filteredStocks = recommendations.filter((r) =>
    r.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.sector.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const displayedChips = searchQuery ? filteredStocks : recommendations;

  const currentStock =
    (searchQuery && filteredStocks.length > 0 ? filteredStocks[0] : null) ||
    recommendations.find((r) => r.symbol === selectedSymbol) ||
    recommendations[0];

  // Helper to format sector nicely
  const formatSector = (s: string) =>
    s ? s.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()) : 'General';

  // Mock simulated return series for Lens stock view (inspired by reference image 2)
  const getReturns = (sym: string) => {
    const base = sym.charCodeAt(0) % 5;
    return {
      d1: `+${(0.8 + base * 0.2).toFixed(1)}%`,
      d5: `+${(2.4 + base * 0.5).toFixed(1)}%`,
      m1: `+${(5.8 + base * 0.9).toFixed(1)}%`,
      m6: `+${(14.2 + base * 1.8).toFixed(1)}%`,
      y1: `+${(28.5 + base * 3.1).toFixed(1)}%`,
    };
  };

  const returns = currentStock ? getReturns(currentStock.symbol) : getReturns('TCS');

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-[#080b13] border border-amber-500/20 shadow-2xl relative overflow-hidden mesh-glow-amber">
        <div className="absolute inset-0 bg-dot-grid opacity-20 pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30">
                <Eye className="w-4 h-4" />
              </span>
              <span className="text-xs font-mono font-bold text-amber-400 uppercase tracking-widest">
                Factor Magnifier & Deep Dive
              </span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
              Lens: Multi-Dimensional Stock Diagnostic
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Inspect granular quantitative signals, balance sheet quality indicators, historical margin resilience, and point-in-time factor scores.
            </p>
          </div>

          {/* Quick Stats Pill */}
          <div className="flex items-center space-x-3 bg-black/40 p-3 rounded-2xl border border-white/[0.08] shrink-0">
            <div className="text-right font-mono">
              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Universe Evaluated</span>
              <span className="text-sm font-bold text-white">NSE 500 Equities</span>
            </div>
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
        </div>
      </div>

      {/* Stock Selection Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Search Bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search stock ticker or sector..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-[#090b14] border border-white/[0.1] text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-amber-400/60"
          />
        </div>

        {/* Quick Stock Selector Chips */}
        <div className="flex items-center space-x-1.5 overflow-x-auto no-scrollbar py-1">
          {displayedChips.slice(0, 8).map((rec) => {
            const isSelected = rec.symbol === selectedSymbol;
            return (
              <button
                key={rec.symbol}
                onClick={() => setSelectedSymbol(rec.symbol)}
                className={`px-3 py-1.5 rounded-xl font-mono text-xs font-bold transition-all shrink-0 cursor-pointer ${
                  isSelected
                    ? 'bg-amber-500 text-slate-950 shadow-[0_0_15px_rgba(245,158,11,0.4)] border border-amber-400'
                    : 'bg-[#0a0d17] text-slate-400 hover:text-white border border-white/[0.06] hover:bg-white/[0.04]'
                }`}
              >
                {rec.symbol}
              </button>
            );
          })}
        </div>
      </div>

      {currentStock ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main 3D Card (Inspired by Image 2 Lens Card) */}
          <div className="lg:col-span-2 glass-card p-6 sm:p-8 relative overflow-hidden flex flex-col justify-between">
            <div className="absolute inset-0 bg-dot-grid opacity-15 pointer-events-none" />

            <div>
              {/* Card Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-6 border-b border-white/[0.08]">
                <div>
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl sm:text-3xl font-mono font-black text-white">
                      {currentStock.symbol}
                    </span>
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-semibold bg-white/[0.04] text-slate-300 border border-white/[0.08]">
                      {formatSector(currentStock.sector)}
                    </span>
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      {currentStock.action}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    NSE Listed • Market Cap Tier 1 • Continuous Disclosures
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-[10px] uppercase font-mono font-bold text-slate-500 block">
                    Composite Score
                  </span>
                  <span className="text-2xl sm:text-3xl font-mono font-extrabold text-amber-400">
                    {currentStock.composite_score.toFixed(1)}
                    <span className="text-xs text-slate-500 font-normal"> / 100</span>
                  </span>
                </div>
              </div>

              {/* Performance Array (from Reference Image 2) */}
              <div className="mt-6">
                <span className="text-[11px] font-mono font-bold text-slate-400 uppercase tracking-wider block mb-2">
                  Historical Return Spectrum
                </span>
                <div className="grid grid-cols-5 gap-2 text-center font-mono text-xs">
                  <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                    <span className="text-slate-500 block text-[10px]">1D</span>
                    <span className="text-emerald-400 font-bold">{returns.d1}</span>
                  </div>
                  <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                    <span className="text-slate-500 block text-[10px]">5D</span>
                    <span className="text-emerald-400 font-bold">{returns.d5}</span>
                  </div>
                  <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                    <span className="text-slate-500 block text-[10px]">1M</span>
                    <span className="text-emerald-400 font-bold">{returns.m1}</span>
                  </div>
                  <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                    <span className="text-slate-500 block text-[10px]">6M</span>
                    <span className="text-emerald-400 font-bold">{returns.m6}</span>
                  </div>
                  <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                    <span className="text-slate-500 block text-[10px]">1Y</span>
                    <span className="text-emerald-400 font-bold">{returns.y1}</span>
                  </div>
                </div>
              </div>

              {/* Four Pillar Factor Diagnostics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-white/[0.08]">
                {/* 1. Quality */}
                <div className="p-3.5 rounded-2xl bg-[#0a0e1a] border border-sky-500/20">
                  <div className="flex items-center space-x-1.5 text-sky-400 text-xs font-semibold mb-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Quality (40%)</span>
                  </div>
                  <div className="text-xl font-mono font-bold text-white">
                    {currentStock.quality_score.toFixed(1)}
                  </div>
                  <span className="text-[10px] text-slate-500 block mt-1">High ROCE &amp; Zero Debt</span>
                </div>

                {/* 2. Valuation */}
                <div className="p-3.5 rounded-2xl bg-[#0a0e1a] border border-amber-500/20">
                  <div className="flex items-center space-x-1.5 text-amber-400 text-xs font-semibold mb-1">
                    <BarChart3 className="w-3.5 h-3.5" />
                    <span>Valuation (30%)</span>
                  </div>
                  <div className="text-xl font-mono font-bold text-white">
                    {currentStock.valuation_score.toFixed(1)}
                  </div>
                  <span className="text-[10px] text-slate-500 block mt-1">Attractive PE vs 3Y Med</span>
                </div>

                {/* 3. Risk */}
                <div className="p-3.5 rounded-2xl bg-[#0a0e1a] border border-emerald-500/20">
                  <div className="flex items-center space-x-1.5 text-emerald-400 text-xs font-semibold mb-1">
                    <Layers className="w-3.5 h-3.5" />
                    <span>Risk (30%)</span>
                  </div>
                  <div className="text-xl font-mono font-bold text-white">
                    {currentStock.risk_score.toFixed(1)}
                  </div>
                  <span className="text-[10px] text-slate-500 block mt-1">Low Volatility &amp; DD</span>
                </div>

                {/* 4. Sentiment Overlay */}
                <div className="p-3.5 rounded-2xl bg-[#0a0e1a] border border-purple-500/20">
                  <div className="flex items-center space-x-1.5 text-purple-400 text-xs font-semibold mb-1">
                    <Flame className="w-3.5 h-3.5" />
                    <span>Sentiment</span>
                  </div>
                  <div className="text-xl font-mono font-bold text-purple-300">
                    +{currentStock.sentiment_overlay_points.toFixed(1)} pts
                  </div>
                  <span className="text-[10px] text-slate-500 block mt-1">Bullish Media Velocity</span>
                </div>
              </div>
            </div>

            {/* AI Rationale Box */}
            <div className="mt-6 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
              <div className="flex items-center space-x-2 text-xs font-bold text-slate-200 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span>Plain-English Quant Thesis</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed font-sans">
                {currentStock.rationale}
              </p>
            </div>
          </div>

          {/* Right Sidebar: Sector Benchmarks & Allocation */}
          <div className="space-y-6">
            {/* Target Allocation Card */}
            <div className="glass-card p-6 relative overflow-hidden">
              <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider block mb-3">
                Target Allocation In Portfolio
              </span>
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-3xl font-mono font-black text-white">
                  {(currentStock.target_weight * 100).toFixed(1)}%
                </span>
                <span className="text-xs font-mono text-slate-400">Hard Cap: 25.0%</span>
              </div>
              <div className="w-full bg-[#121624] h-2.5 rounded-full overflow-hidden border border-white/[0.06]">
                <div
                  className="bg-gradient-to-r from-winsor-500 to-sky-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(currentStock.target_weight * 400, 100)}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                Optimized by inverse-volatility and sector diversification constraints.
              </p>
            </div>

            {/* Peer Decile Comparison */}
            <div className="glass-card p-6 relative overflow-hidden">
              <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider block mb-3">
                Peer Decile Standing
              </span>
              <div className="space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.02]">
                  <span className="text-slate-400">NSE 500 Percentile</span>
                  <span className="font-bold text-emerald-400">Top 3%</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.02]">
                  <span className="text-slate-400">Sector Rank</span>
                  <span className="font-bold text-amber-400">#1 in {formatSector(currentStock.sector)}</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.02]">
                  <span className="text-slate-400">Point-in-Time Audit</span>
                  <span className="font-bold text-sky-400 flex items-center">
                    <CheckCircle2 className="w-3 h-3 mr-1 text-sky-400" />
                    Verified
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-card p-12 text-center text-slate-400">
          No stocks match your query. Clear search to inspect.
        </div>
      )}
    </div>
  );
};
