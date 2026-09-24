import React, { useState } from 'react';
import {
  ChevronRight,
  AlertTriangle,
  Bell,
  Sparkles,
  Bot,
  User,
  ArrowUpRight,
} from 'lucide-react';

interface FiveToolsBentoProps {
  onSelectTool?: (toolId: string, subToolId?: string) => void;
}

export const FiveToolsBento: React.FC<FiveToolsBentoProps> = ({ onSelectTool }) => {
  // Artha AI interactive query state
  const [selectedQuestionIdx, setSelectedQuestionIdx] = useState<number>(0);

  const aiQueries = [
    {
      q: "Why is TCS ranked #1 in Quality?",
      a: "TCS achieves a 96/100 Quality Score via 48.2% ROCE, 0.0 debt-to-equity, and 12 consecutive quarters of operating margin stability above 24%.",
    },
    {
      q: "How does the Point-in-Time audit prevent lookahead bias?",
      a: "Financial metrics are indexed by exact public disclosure timestamps rather than quarter-end dates, strictly barring future restatements from historical rebalances.",
    },
    {
      q: "Why does the model enforce a 25% sector cap?",
      a: "Sector diversification caps prevent idiosyncratic industry contagion while maximizing Sharpe ratio across varying interest rate cycles.",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Section Title Header (Inspired by Image 2) */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <span className="text-xs font-semibold text-winsor-400 uppercase tracking-widest flex items-center">
            <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-400" />
            Institutional Architecture
          </span>
          <h2 className="text-2xl sm:text-4xl font-black text-white tracking-tight mt-1">
            Explore Our Five Powerful Tools
          </h2>
        </div>

        <button
          onClick={() => onSelectTool && onSelectTool('recommendations', 'alpha_picks')}
          className="self-start sm:self-auto px-4 py-1.5 rounded-full bg-[#11131d] border border-white/[0.1] text-xs font-semibold text-slate-200 hover:border-winsor-500/50 hover:text-white transition-all shadow-sm cursor-pointer"
        >
          Launch Full Terminal
        </button>
      </div>

      {/* The 2x2 + 1 Bento Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tool 1: Lens (Amber/Copper Glow) */}
        <div className="glass-card p-6 relative overflow-hidden flex flex-col justify-between group mesh-glow-amber">
          <div className="absolute inset-0 bg-dot-grid opacity-20 pointer-events-none" />

          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold text-white tracking-tight">Lens</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
                FACTOR ANALYSIS
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-2 max-w-md">
              See every stock clearly — from fundamentals to trends and sentiment, all in one view.
            </p>
            <button
              onClick={() => onSelectTool && onSelectTool('recommendations', 'lens')}
              className="mt-3 text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center group-hover:translate-x-1 transition-transform cursor-pointer"
            >
              <span>Explore Stock Factors</span>
              <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
            </button>
          </div>

          {/* Embedded Mockup: 3D-styled Stock Card (from Image 2) */}
          <div className="mt-6 p-4 rounded-2xl bg-[#090b13] border border-white/[0.08] shadow-2xl relative">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-black text-sm text-white">RELIANCE</span>
                  <span className="text-[10px] text-slate-400">Reliance Industries Ltd</span>
                </div>
                <div className="flex items-baseline space-x-2 mt-1">
                  <span className="text-xl font-mono font-extrabold text-white">₹2,940.00</span>
                  <span className="text-xs font-mono font-bold text-emerald-400">+1.24% (+36.00)</span>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[10px] uppercase text-slate-500 font-bold block">Composite Rank</span>
                <span className="text-base font-mono font-extrabold text-amber-400">#1 Top Pick</span>
              </div>
            </div>

            {/* Performance Array */}
            <div className="grid grid-cols-5 gap-2 mt-4 pt-3 border-t border-white/[0.06] text-center font-mono text-[10px]">
              <div className="bg-white/[0.02] p-1.5 rounded-lg">
                <span className="text-slate-500 block">1D</span>
                <span className="text-emerald-400 font-bold">+1.2%</span>
              </div>
              <div className="bg-white/[0.02] p-1.5 rounded-lg">
                <span className="text-slate-500 block">5D</span>
                <span className="text-emerald-400 font-bold">+3.4%</span>
              </div>
              <div className="bg-white/[0.02] p-1.5 rounded-lg">
                <span className="text-slate-500 block">1M</span>
                <span className="text-emerald-400 font-bold">+8.3%</span>
              </div>
              <div className="bg-white/[0.02] p-1.5 rounded-lg">
                <span className="text-slate-500 block">6M</span>
                <span className="text-emerald-400 font-bold">+21.2%</span>
              </div>
              <div className="bg-white/[0.02] p-1.5 rounded-lg">
                <span className="text-slate-500 block">1Y</span>
                <span className="text-emerald-400 font-bold">+32.4%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Tool 2: Vault (Golden Yellow Glow) */}
        <div className="glass-card p-6 relative overflow-hidden flex flex-col justify-between group mesh-glow-gold">
          <div className="absolute inset-0 bg-dot-grid opacity-20 pointer-events-none" />

          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold text-white tracking-tight">Vault</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400 border border-yellow-500/30">
                PORTFOLIO ALLOCATION
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-2 max-w-md">
              Understand your funds — track performance, see what's inside, and compare easily.
            </p>
            <button
              onClick={() => onSelectTool && onSelectTool('portfolio')}
              className="mt-3 text-xs font-semibold text-yellow-400 hover:text-yellow-300 flex items-center group-hover:translate-x-1 transition-transform cursor-pointer"
            >
              <span>View Portfolio & Sector Caps</span>
              <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
            </button>
          </div>

          {/* Embedded Mockup: Fund Diversification Ring (from Image 2) */}
          <div className="mt-6 p-4 rounded-2xl bg-[#090b13] border border-white/[0.08] shadow-2xl flex items-center justify-between">
            <div className="space-y-2 text-xs">
              <span className="text-[11px] uppercase font-bold text-slate-400">Sector Exposures</span>
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
                <span className="text-slate-300">Technology: <strong className="text-white font-mono">24.5%</strong></span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
                <span className="text-slate-300">Energy: <strong className="text-white font-mono">22.0%</strong></span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                <span className="text-slate-300">Financials: <strong className="text-white font-mono">19.5%</strong></span>
              </div>
            </div>

            {/* SVG Donut Ring */}
            <div className="relative w-24 h-24 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="14" fill="none" stroke="#151a28" strokeWidth="4" />
                <circle
                  cx="18"
                  cy="18"
                  r="14"
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="4"
                  strokeDasharray="30 100"
                  strokeLinecap="round"
                />
                <circle
                  cx="18"
                  cy="18"
                  r="14"
                  fill="none"
                  stroke="#facc15"
                  strokeWidth="4"
                  strokeDasharray="25 100"
                  strokeDashoffset="-32"
                  strokeLinecap="round"
                />
                <circle
                  cx="18"
                  cy="18"
                  r="14"
                  fill="none"
                  stroke="#34d399"
                  strokeWidth="4"
                  strokeDasharray="20 100"
                  strokeDashoffset="-60"
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-[11px] font-mono font-bold text-white">&lt;25%</span>
                <span className="text-[8px] text-slate-400">HARD CAP</span>
              </div>
            </div>
          </div>
        </div>

        {/* Tool 3: Pulse (Coral/Cyan Thematic Radar) */}
        <div className="glass-card p-6 relative overflow-hidden flex flex-col justify-between group mesh-glow-cyan">
          <div className="absolute inset-0 bg-dot-grid opacity-20 pointer-events-none" />

          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold text-white tracking-tight">Pulse</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                THEMATIC RADAR
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-2 max-w-md">
              Discover what's trending — invest by theme, from AI and clean energy to Capex and PSU dividends.
            </p>
            <button
              onClick={() => onSelectTool && onSelectTool('recommendations', 'radar')}
              className="mt-3 text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center group-hover:translate-x-1 transition-transform cursor-pointer"
            >
              <span>Scan Market Themes</span>
              <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
            </button>
          </div>

          {/* Embedded Mockup: Connected Neural Constellation Graph (from Image 2) */}
          <div className="mt-6 p-4 rounded-2xl bg-[#090b13] border border-white/[0.08] shadow-2xl relative overflow-hidden">
            <span className="text-[11px] uppercase font-bold text-slate-400 block mb-2">
              Trending Quant Clusters
            </span>

            {/* Simulated Constellation Canvas */}
            <div className="relative h-28 flex items-center justify-center">
              <svg className="absolute inset-0 w-full h-full pointer-events-none stroke-cyan-500/30">
                <line x1="20%" y1="50%" x2="50%" y2="25%" strokeWidth="1" strokeDasharray="3 3" />
                <line x1="50%" y1="25%" x2="80%" y2="50%" strokeWidth="1" strokeDasharray="3 3" />
                <line x1="20%" y1="50%" x2="50%" y2="75%" strokeWidth="1" strokeDasharray="3 3" />
                <line x1="50%" y1="75%" x2="80%" y2="50%" strokeWidth="1" strokeDasharray="3 3" />
              </svg>

              {/* Glowing Theme Badges */}
              <div className="flex flex-wrap items-center justify-center gap-3 z-10">
                <span className="px-3.5 py-1.5 rounded-xl bg-cyan-950/60 border border-cyan-400/40 text-cyan-300 font-bold text-xs shadow-[0_0_15px_rgba(6,182,212,0.3)]">
                  AI & Tech
                </span>
                <span className="px-3.5 py-1.5 rounded-xl bg-emerald-950/60 border border-emerald-400/40 text-emerald-300 font-bold text-xs shadow-[0_0_15px_rgba(16,185,129,0.3)]">
                  Green Capex
                </span>
                <span className="px-3.5 py-1.5 rounded-xl bg-indigo-950/60 border border-indigo-400/40 text-indigo-300 font-bold text-xs shadow-[0_0_15px_rgba(99,102,241,0.3)]">
                  High ROCE
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tool 4: Edge (Royal Purple Glow) */}
        <div className="glass-card p-6 relative overflow-hidden flex flex-col justify-between group mesh-glow-purple">
          <div className="absolute inset-0 bg-dot-grid opacity-20 pointer-events-none" />

          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold text-white tracking-tight">Edge</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/30">
                REAL-TIME ALERTS
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-2 max-w-md">
              Get real-time alerts on earnings, events, and shifts — never miss a move.
            </p>
            <button
              onClick={() => onSelectTool && onSelectTool('recommendations', 'radar')}
              className="mt-3 text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center group-hover:translate-x-1 transition-transform cursor-pointer"
            >
              <span>Inspect Point-in-Time Stream</span>
              <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
            </button>
          </div>

          {/* Embedded Mockup: Market Signals & Alert Pill (from Image 5) */}
          <div className="mt-6 p-4 rounded-2xl bg-[#090b13] border border-white/[0.08] shadow-2xl space-y-2">
            <div className="flex items-center justify-between p-2 rounded-xl bg-emerald-950/30 border border-emerald-500/30">
              <div className="flex items-center space-x-2">
                <Bell className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs text-slate-200">
                  <strong className="text-white font-mono">TCS</strong> Q3 Disclosure Verified (+8.2% PAT)
                </span>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 font-bold">LIVE</span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-xl bg-amber-950/30 border border-amber-500/30">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-xs text-slate-200">
                  <strong className="text-white font-mono">INDIA VIX</strong> 12.84: Low-Risk Regime Active
                </span>
              </div>
              <span className="text-[10px] font-mono text-amber-400 font-bold">INFO</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tool 5: Artha AI Copilot (Wide Full Card, Emerald Glow, inspired by Patricia in Image 5) */}
      <div className="glass-card p-6 sm:p-8 relative overflow-hidden mesh-glow-emerald">
        <div className="absolute inset-0 bg-dot-grid opacity-20 pointer-events-none" />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          {/* Left Title & Info */}
          <div className="lg:col-span-5">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)]">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white tracking-tight">Artha AI</h3>
                <span className="text-[10px] font-mono text-emerald-400 font-bold">
                  QUANT INTELLIGENCE COPILOT
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-300 mt-3 leading-relaxed">
              Meet Artha AI — your quantitative copilot for smarter investing. Ask anything and get clear,
              mathematically validated answers.
            </p>

            {/* Query Selector Tabs */}
            <div className="mt-4 space-y-1.5">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Ask a Sample Question:
              </span>
              {aiQueries.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedQuestionIdx(idx)}
                  className={`w-full text-left px-3 py-2 rounded-xl text-xs transition-all flex items-center justify-between ${
                    selectedQuestionIdx === idx
                      ? 'bg-emerald-950/60 border border-emerald-400/50 text-white font-semibold'
                      : 'bg-white/[0.02] border border-white/[0.04] text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className="truncate pr-2">{item.q}</span>
                  <ArrowUpRight className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                </button>
              ))}
            </div>
          </div>

          {/* Right Simulated Conversational Dialogue */}
          <div className="lg:col-span-7 bg-[#090b13] p-5 rounded-2xl border border-white/[0.08] shadow-2xl space-y-4">
            {/* User Prompt */}
            <div className="flex items-start space-x-3">
              <div className="w-7 h-7 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center text-slate-300 shrink-0">
                <User className="w-3.5 h-3.5" />
              </div>
              <div className="p-3 rounded-2xl rounded-tl-none bg-[#121624] border border-white/[0.06] text-xs text-white max-w-lg">
                {aiQueries[selectedQuestionIdx].q}
              </div>
            </div>

            {/* Artha AI Response */}
            <div className="flex items-start space-x-3">
              <div className="w-7 h-7 rounded-full bg-emerald-600/30 border border-emerald-400/50 flex items-center justify-center text-emerald-400 shrink-0 shadow-[0_0_10px_rgba(16,185,129,0.3)]">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="p-3 rounded-2xl rounded-tl-none bg-emerald-950/20 border border-emerald-500/20 text-xs text-slate-200 max-w-lg leading-relaxed font-sans">
                {aiQueries[selectedQuestionIdx].a}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
