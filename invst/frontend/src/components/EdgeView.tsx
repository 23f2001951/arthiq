import React, { useState } from 'react';
import {
  Zap,
  CheckCircle2,
  ArrowUpRight,
} from 'lucide-react';

interface MarketSignal {
  id: string;
  symbol: string;
  companyName: string;
  category: 'earnings' | 'breakout' | 'factor' | 'risk';
  headline: string;
  timestamp: string;
  scoreImpact: string;
  sentimentTone: 'bullish' | 'neutral' | 'cautious';
  pitVerified: boolean;
}

const SIGNALS: MarketSignal[] = [
  {
    id: 'sig-1',
    symbol: 'TCS',
    companyName: 'Tata Consultancy Services Ltd',
    category: 'earnings',
    headline: 'Q3 Financial Disclosure Verified: PAT climbs +8.2% YoY, EBIT margin holds firm at 25.1%.',
    timestamp: '14 mins ago',
    scoreImpact: '+4.5 Factor Pts',
    sentimentTone: 'bullish',
    pitVerified: true,
  },
  {
    id: 'sig-2',
    symbol: 'INFY',
    companyName: 'Infosys Ltd',
    category: 'breakout',
    headline: 'Volume Momentum Surge: 30-day median trading velocity exceeded by 2.4x with price up +1.9%.',
    timestamp: '32 mins ago',
    scoreImpact: '+3.2 Factor Pts',
    sentimentTone: 'bullish',
    pitVerified: true,
  },
  {
    id: 'sig-3',
    symbol: 'ICICIBANK',
    companyName: 'ICICI Bank Ltd',
    category: 'factor',
    headline: 'Rank Upgrade: Advances into top decile (Decile 1) across Quality & Risk dimensions.',
    timestamp: '1 hr ago',
    scoreImpact: 'Rank #2 Overall',
    sentimentTone: 'bullish',
    pitVerified: true,
  },
  {
    id: 'sig-4',
    symbol: 'RELIANCE',
    companyName: 'Reliance Industries Ltd',
    category: 'earnings',
    headline: 'Energy & Retail Capex Filing: New green hydrogen facility capitalised without leverage increase.',
    timestamp: '2 hrs ago',
    scoreImpact: '+2.8 Factor Pts',
    sentimentTone: 'bullish',
    pitVerified: true,
  },
  {
    id: 'sig-5',
    symbol: 'BHARTIARTL',
    companyName: 'Bharti Airtel Ltd',
    category: 'breakout',
    headline: 'ARPU Expansion Alert: Blended ARPU expands past ₹210 on 5G plan migrations.',
    timestamp: '3 hrs ago',
    scoreImpact: '+3.0 Factor Pts',
    sentimentTone: 'bullish',
    pitVerified: true,
  },
  {
    id: 'sig-6',
    symbol: 'LT',
    companyName: 'Larsen & Toubro Ltd',
    category: 'factor',
    headline: 'Mega Order Win Disclosed: ₹4,200 Cr hydrocarbon contract secured in Middle East.',
    timestamp: '4 hrs ago',
    scoreImpact: '+2.5 Factor Pts',
    sentimentTone: 'bullish',
    pitVerified: true,
  },
  {
    id: 'sig-7',
    symbol: 'HDFCBANK',
    companyName: 'HDFC Bank Ltd',
    category: 'risk',
    headline: 'Credit-Deposit Ratio Consolidation: Margin expansion on track following merger integration.',
    timestamp: '5 hrs ago',
    scoreImpact: 'Neutral Drift',
    sentimentTone: 'neutral',
    pitVerified: true,
  },
];

export const EdgeView: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const filteredSignals =
    selectedCategory === 'all'
      ? SIGNALS
      : SIGNALS.filter((s) => s.category === selectedCategory);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-[#080b13] border border-purple-500/20 shadow-2xl relative overflow-hidden mesh-glow-purple">
        <div className="absolute inset-0 bg-dot-grid opacity-20 pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/30">
                <Zap className="w-4 h-4" />
              </span>
              <span className="text-xs font-mono font-bold text-purple-400 uppercase tracking-widest">
                Real-Time Event Radar &amp; Point-in-Time Disclosures
              </span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
              Edge: Quantitative Event Stream
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Streaming disclosures, volume breakouts, and model rank migrations audited against zero-lookahead timestamps.
            </p>
          </div>

          <div className="flex items-center space-x-3 bg-black/40 p-3 rounded-2xl border border-white/[0.08] shrink-0 font-mono">
            <div className="text-right">
              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Feed Status</span>
              <span className="text-sm font-bold text-emerald-400 flex items-center justify-end">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
                Live PIT Stream
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Signal Filter Bar */}
      <div className="flex items-center space-x-2 overflow-x-auto no-scrollbar py-1 font-mono text-xs">
        <button
          onClick={() => setSelectedCategory('all')}
          className={`px-4 py-1.5 rounded-full font-bold transition-all cursor-pointer ${
            selectedCategory === 'all'
              ? 'bg-purple-600 text-white shadow-[0_0_15px_rgba(147,51,234,0.4)] border border-purple-400'
              : 'bg-[#0a0d18] text-slate-400 hover:text-white border border-white/[0.06]'
          }`}
        >
          All Signals ({SIGNALS.length})
        </button>
        <button
          onClick={() => setSelectedCategory('earnings')}
          className={`px-4 py-1.5 rounded-full font-bold transition-all cursor-pointer ${
            selectedCategory === 'earnings'
              ? 'bg-purple-600 text-white shadow-[0_0_15px_rgba(147,51,234,0.4)] border border-purple-400'
              : 'bg-[#0a0d18] text-slate-400 hover:text-white border border-white/[0.06]'
          }`}
        >
          Earnings &amp; Results
        </button>
        <button
          onClick={() => setSelectedCategory('breakout')}
          className={`px-4 py-1.5 rounded-full font-bold transition-all cursor-pointer ${
            selectedCategory === 'breakout'
              ? 'bg-purple-600 text-white shadow-[0_0_15px_rgba(147,51,234,0.4)] border border-purple-400'
              : 'bg-[#0a0d18] text-slate-400 hover:text-white border border-white/[0.06]'
          }`}
        >
          Volume &amp; Breakouts
        </button>
        <button
          onClick={() => setSelectedCategory('factor')}
          className={`px-4 py-1.5 rounded-full font-bold transition-all cursor-pointer ${
            selectedCategory === 'factor'
              ? 'bg-purple-600 text-white shadow-[0_0_15px_rgba(147,51,234,0.4)] border border-purple-400'
              : 'bg-[#0a0d18] text-slate-400 hover:text-white border border-white/[0.06]'
          }`}
        >
          Factor Upgrades
        </button>
        <button
          onClick={() => setSelectedCategory('risk')}
          className={`px-4 py-1.5 rounded-full font-bold transition-all cursor-pointer ${
            selectedCategory === 'risk'
              ? 'bg-purple-600 text-white shadow-[0_0_15px_rgba(147,51,234,0.4)] border border-purple-400'
              : 'bg-[#0a0d18] text-slate-400 hover:text-white border border-white/[0.06]'
          }`}
        >
          Risk Diagnostics
        </button>
      </div>

      {/* Signals Stream List */}
      <div className="space-y-4">
        {filteredSignals.map((signal) => (
          <div
            key={signal.id}
            className="glass-card p-5 sm:p-6 relative overflow-hidden hover:border-purple-500/40 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
          >
            <div className="space-y-2 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono font-black text-white text-base">{signal.symbol}</span>
                <span className="text-xs text-slate-400 hidden md:inline">({signal.companyName})</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/[0.04] text-slate-400 border border-white/[0.08] uppercase">
                  {signal.category}
                </span>
                <span className="text-[10px] font-mono text-emerald-400 flex items-center bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  <CheckCircle2 className="w-2.5 h-2.5 mr-1" />
                  PIT Timestamped
                </span>
                <span className="text-[10px] font-mono text-slate-500 ml-auto sm:ml-0">
                  {signal.timestamp}
                </span>
              </div>

              <p className="text-xs sm:text-sm text-slate-200 font-sans leading-relaxed">
                {signal.headline}
              </p>
            </div>

            <div className="flex items-center space-x-3 shrink-0 sm:border-l sm:border-white/[0.06] sm:pl-6">
              <div className="text-right font-mono">
                <span className="text-[10px] text-slate-500 uppercase block font-semibold">Model Impact</span>
                <span className="text-xs sm:text-sm font-bold text-amber-400">{signal.scoreImpact}</span>
              </div>
              <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 group-hover:scale-110 transition-transform">
                <ArrowUpRight className="w-4 h-4" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
