import React, { useState } from 'react';
import {
  Activity,
  Sparkles,
  Cpu,
  Leaf,
  Building2,
  Shield,
} from 'lucide-react';

interface PulseTheme {
  id: string;
  name: string;
  category: string;
  tagline: string;
  stocks: { symbol: string; weight: string; change: string }[];
  avgScore: number;
  sentiment: string;
  colorScheme: {
    badge: string;
    border: string;
    glow: string;
    icon: React.ComponentType<{ className?: string }>;
  };
}

const THEMES: PulseTheme[] = [
  {
    id: 'ai_tech',
    name: 'AI & Enterprise Tech',
    category: 'INNOVATION',
    tagline: 'Leading cloud migration, genAI tooling, and large-scale digital architecture.',
    stocks: [
      { symbol: 'TCS', weight: '28%', change: '+1.8%' },
      { symbol: 'INFY', weight: '26%', change: '+2.4%' },
      { symbol: 'HCLTECH', weight: '24%', change: '+1.1%' },
      { symbol: 'TECHM', weight: '22%', change: '+3.2%' },
    ],
    avgScore: 91.4,
    sentiment: 'Bullish (+8.4 pts)',
    colorScheme: {
      badge: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
      border: 'border-cyan-500/20 hover:border-cyan-400/50',
      glow: 'mesh-glow-cyan',
      icon: Cpu,
    },
  },
  {
    id: 'green_capex',
    name: 'Energy Transition & Clean Capex',
    category: 'SUSTAINABILITY',
    tagline: 'Solar generation, grid transmission modernisation, and hydrogen infrastructure.',
    stocks: [
      { symbol: 'RELIANCE', weight: '32%', change: '+1.5%' },
      { symbol: 'NTPC', weight: '25%', change: '+0.9%' },
      { symbol: 'POWERGRID', weight: '23%', change: '+0.6%' },
      { symbol: 'TATAPOWER', weight: '20%', change: '+2.8%' },
    ],
    avgScore: 88.2,
    sentiment: 'Very Bullish (+9.2 pts)',
    colorScheme: {
      badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      border: 'border-emerald-500/20 hover:border-emerald-400/50',
      glow: 'mesh-glow-emerald',
      icon: Leaf,
    },
  },
  {
    id: 'high_roce',
    name: 'High ROCE Compounding Titans',
    category: 'QUALITY LEADER',
    tagline: 'Moated business models with negative working capital and >35% return on capital.',
    stocks: [
      { symbol: 'TCS', weight: '30%', change: '+1.8%' },
      { symbol: 'NESTLEIND', weight: '25%', change: '+0.4%' },
      { symbol: 'TITAN', weight: '25%', change: '+1.9%' },
      { symbol: 'ITC', weight: '20%', change: '+0.7%' },
    ],
    avgScore: 94.6,
    sentiment: 'Steady (+6.8 pts)',
    colorScheme: {
      badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      border: 'border-amber-500/20 hover:border-amber-400/50',
      glow: 'mesh-glow-amber',
      icon: Sparkles,
    },
  },
  {
    id: 'credit_expansion',
    name: 'Private Banking & Credit Expansion',
    category: 'FINANCIAL SERVICES',
    tagline: 'Corporate capex financing, robust retail loan books, and declining NPA ratios.',
    stocks: [
      { symbol: 'ICICIBANK', weight: '34%', change: '+1.2%' },
      { symbol: 'HDFCBANK', weight: '30%', change: '+0.5%' },
      { symbol: 'AXISBANK', weight: '20%', change: '+1.4%' },
      { symbol: 'KOTAKBANK', weight: '16%', change: '+0.8%' },
    ],
    avgScore: 89.0,
    sentiment: 'Positive (+7.1 pts)',
    colorScheme: {
      badge: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
      border: 'border-sky-500/20 hover:border-sky-400/50',
      glow: 'mesh-glow-cyan',
      icon: Building2,
    },
  },
  {
    id: 'defense_infra',
    name: 'Defense & Make-in-India Supercycle',
    category: 'INDUSTRIAL',
    tagline: 'Record multi-year order books backed by indigenisation mandates and export ramp.',
    stocks: [
      { symbol: 'LT', weight: '35%', change: '+2.1%' },
      { symbol: 'BEL', weight: '25%', change: '+3.4%' },
      { symbol: 'HAL', weight: '22%', change: '+2.9%' },
      { symbol: 'BHARATFORG', weight: '18%', change: '+1.6%' },
    ],
    avgScore: 92.1,
    sentiment: 'Strong (+8.9 pts)',
    colorScheme: {
      badge: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
      border: 'border-purple-500/20 hover:border-purple-400/50',
      glow: 'mesh-glow-purple',
      icon: Shield,
    },
  },
];

export const PulseView: React.FC = () => {
  const [selectedThemeId, setSelectedThemeId] = useState<string>('ai_tech');

  const selectedTheme = THEMES.find((t) => t.id === selectedThemeId) || THEMES[0];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-[#080b13] border border-cyan-500/20 shadow-2xl relative overflow-hidden mesh-glow-cyan">
        <div className="absolute inset-0 bg-dot-grid opacity-20 pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                <Activity className="w-4 h-4" />
              </span>
              <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-widest">
                Thematic Quant Cluster Radar
              </span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
              Pulse: Real-Time Market Themes
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Uncover institutional capital rotation themes — identify cohesive momentum clusters across NSE 500 sectors before retail discovery.
            </p>
          </div>

          <div className="flex items-center space-x-3 bg-black/40 p-3 rounded-2xl border border-white/[0.08] shrink-0 font-mono">
            <div className="text-right">
              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Active Quant Clusters</span>
              <span className="text-sm font-bold text-white">{THEMES.length} Monitored Themes</span>
            </div>
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          </div>
        </div>
      </div>

      {/* Neural Constellation Visualizer (from Image 2 Pulse Card) */}
      <div className="glass-card p-6 sm:p-8 relative overflow-hidden">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
            Connected Factor Neural Constellation
          </span>
          <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/30">
            DYNAMIC CLUSTERING
          </span>
        </div>

        {/* Canvas Area with Constellation Lines and Glowing Theme Nodes */}
        <div className="relative h-44 sm:h-52 rounded-2xl bg-[#090b14] border border-white/[0.06] flex items-center justify-center overflow-hidden">
          <svg className="absolute inset-0 w-full h-full pointer-events-none stroke-cyan-500/25">
            <line x1="15%" y1="50%" x2="35%" y2="25%" strokeWidth="1.5" strokeDasharray="4 4" />
            <line x1="35%" y1="25%" x2="65%" y2="25%" strokeWidth="1.5" strokeDasharray="4 4" />
            <line x1="65%" y1="25%" x2="85%" y2="50%" strokeWidth="1.5" strokeDasharray="4 4" />
            <line x1="15%" y1="50%" x2="35%" y2="75%" strokeWidth="1.5" strokeDasharray="4 4" />
            <line x1="35%" y1="75%" x2="65%" y2="75%" strokeWidth="1.5" strokeDasharray="4 4" />
            <line x1="65%" y1="75%" x2="85%" y2="50%" strokeWidth="1.5" strokeDasharray="4 4" />
            <line x1="35%" y1="25%" x2="65%" y2="75%" strokeWidth="1" strokeDasharray="2 2" />
            <line x1="35%" y1="75%" x2="65%" y2="25%" strokeWidth="1" strokeDasharray="2 2" />
          </svg>

          {/* Interactive Cluster Nodes */}
          <div className="relative z-10 flex flex-wrap items-center justify-center gap-3 sm:gap-6 px-4">
            {THEMES.map((theme) => {
              const isSelected = theme.id === selectedThemeId;
              const Icon = theme.colorScheme.icon;
              return (
                <button
                  key={theme.id}
                  onClick={() => setSelectedThemeId(theme.id)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-2xl font-bold text-xs sm:text-sm transition-all duration-300 cursor-pointer ${
                    isSelected
                      ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-[0_0_25px_rgba(6,182,212,0.5)] border border-cyan-300 scale-105'
                      : 'bg-[#101422]/90 text-slate-300 hover:text-white border border-white/[0.1] hover:border-cyan-400/40'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{theme.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected Theme Deep-Dive Card */}
      <div className="glass-card p-6 sm:p-8 relative overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-white/[0.08]">
          <div>
            <div className="flex items-center space-x-3">
              <h3 className="text-xl sm:text-2xl font-black text-white">{selectedTheme.name}</h3>
              <span className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full border ${selectedTheme.colorScheme.badge}`}>
                {selectedTheme.category}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">{selectedTheme.tagline}</p>
          </div>

          <div className="flex items-center space-x-4 font-mono text-right">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Theme Score</span>
              <span className="text-2xl font-extrabold text-cyan-400">{selectedTheme.avgScore.toFixed(1)}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Sentiment Overlay</span>
              <span className="text-xs font-bold text-emerald-400">{selectedTheme.sentiment}</span>
            </div>
          </div>
        </div>

        {/* Constituent Stocks Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {selectedTheme.stocks.map((stock) => (
            <div
              key={stock.symbol}
              className="p-4 rounded-2xl bg-[#090b14] border border-white/[0.08] hover:border-cyan-400/30 transition-all flex items-center justify-between"
            >
              <div>
                <span className="font-mono font-bold text-white text-base block">{stock.symbol}</span>
                <span className="text-[10px] font-mono text-slate-400">Basket Weight: {stock.weight}</span>
              </div>
              <div className="text-right font-mono">
                <span className="text-xs font-bold text-emerald-400 block">{stock.change}</span>
                <span className="text-[9px] text-slate-500">TODAY</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
