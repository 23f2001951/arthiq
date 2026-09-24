import React, { useState } from 'react';
import { Sparkles, ChevronDown, ArrowUpRight, TrendingUp } from 'lucide-react';

interface BarData {
  label: string;
  factor: string;
  value: number; // in thousands or percentage
  heightPercent: number; // 20 - 100
  isHighlight?: boolean;
}

const DEFAULT_BARS: BarData[] = [
  { label: 'W1', factor: 'Earnings Yield', value: 18.2, heightPercent: 45 },
  { label: 'W2', factor: 'Price Momentum', value: 20.4, heightPercent: 55 },
  { label: 'W3', factor: 'Low Volatility', value: 22.8, heightPercent: 68 },
  { label: 'W4', factor: 'Quality / ROE', value: 28.5, heightPercent: 92, isHighlight: true },
  { label: 'W5', factor: 'Debt to Equity', value: 17.5, heightPercent: 42 },
  { label: 'W6', factor: 'Earnings Growth', value: 19.8, heightPercent: 52 },
  { label: 'W7', factor: 'Alpha Composite', value: 23.6, heightPercent: 72 },
];

export const CapsuleBarChart: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'alpha' | 'flow' | 'factors'>('alpha');
  const [timeframe, setTimeframe] = useState<'Weekly' | 'Monthly' | 'Quarterly'>('Weekly');
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(3);

  return (
    <div className="glass-card p-6 relative overflow-hidden flex flex-col justify-between">
      {/* Top Bar with Title & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <span className="text-xs font-semibold tracking-wider text-winsor-400 uppercase flex items-center">
            <Sparkles className="w-3.5 h-3.5 mr-1" />
            Quant Capital & Factor Dynamics
          </span>
          <div className="flex items-baseline space-x-2 mt-1">
            <h2 className="text-3xl font-extrabold font-mono text-white tracking-tight">
              ₹2,48,500
              <span className="text-sm font-semibold text-emerald-400 ml-2 font-mono">
                +18.42%
              </span>
            </h2>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          {/* Filter Pills */}
          <div className="flex bg-[#07090f] p-1 rounded-xl border border-white/[0.08]">
            <button
              onClick={() => setActiveTab('alpha')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                activeTab === 'alpha'
                  ? 'bg-winsor-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.6)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Alpha
            </button>
            <button
              onClick={() => setActiveTab('flow')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                activeTab === 'flow'
                  ? 'bg-winsor-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.6)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Inflow
            </button>
            <button
              onClick={() => setActiveTab('factors')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                activeTab === 'factors'
                  ? 'bg-winsor-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.6)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Factors
            </button>
          </div>

          {/* Timeframe selector dropdown */}
          <div className="relative">
            <button
              onClick={() =>
                setTimeframe(
                  timeframe === 'Weekly'
                    ? 'Monthly'
                    : timeframe === 'Monthly'
                    ? 'Quarterly'
                    : 'Weekly'
                )
              }
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[#0b0e17] border border-white/[0.08] text-xs font-semibold text-slate-300 hover:border-winsor-500/40 transition-colors"
            >
              <span>{timeframe}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="relative h-64 mt-4 w-full flex items-end justify-between px-2 sm:px-6 pt-10">
        {/* Horizontal subtle guide lines */}
        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20">
          <div className="border-b border-dashed border-slate-600 flex justify-between text-[10px] text-slate-500 font-mono">
            <span>28k</span>
          </div>
          <div className="border-b border-dashed border-slate-600 flex justify-between text-[10px] text-slate-500 font-mono">
            <span>22k</span>
          </div>
          <div className="border-b border-dashed border-slate-600 flex justify-between text-[10px] text-slate-500 font-mono">
            <span>18k</span>
          </div>
          <div className="border-b border-dashed border-slate-600 flex justify-between text-[10px] text-slate-500 font-mono">
            <span>15k</span>
          </div>
        </div>

        {/* Center spotlight beam over the highest bar */}
        <div className="absolute left-[45%] top-0 w-32 h-64 spotlight-beam pointer-events-none blur-xl -translate-x-1/2 opacity-75" />

        {/* Capsule Pillar Bars */}
        {DEFAULT_BARS.map((bar, idx) => {
          const isHovered = hoveredIdx === idx;
          const isLeader = bar.isHighlight;

          return (
            <div
              key={idx}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(idx)}
              className="relative flex flex-col items-center justify-end h-full z-10 group cursor-pointer"
              style={{ width: `${100 / DEFAULT_BARS.length - 3}%` }}
            >
              {/* Tooltip on hover */}
              {isHovered && (
                <div className="absolute -top-10 z-30 px-2.5 py-1 rounded-lg bg-obsidian-900 border border-winsor-500/50 shadow-xl shadow-black/80 whitespace-nowrap text-center animate-fadeIn">
                  <p className="text-[10px] font-semibold text-winsor-300">{bar.factor}</p>
                  <p className="text-xs font-mono font-bold text-white">
                    ₹{(bar.value * 1000).toLocaleString('en-IN')}
                  </p>
                </div>
              )}

              {/* Glowing Beacon Dot on Top of the Pillar */}
              <div
                className={`w-3.5 h-3.5 rounded-full mb-1 transition-all duration-300 flex items-center justify-center ${
                  isLeader
                    ? 'bg-sky-400 shadow-[0_0_14px_rgba(56,189,248,1)] beacon-dot'
                    : isHovered
                    ? 'bg-winsor-400 shadow-[0_0_10px_rgba(37,99,235,0.9)]'
                    : 'bg-white/60 shadow-[0_0_6px_rgba(255,255,255,0.6)]'
                }`}
              >
                <div className="w-1.5 h-1.5 rounded-full bg-white" />
              </div>

              {/* The Domed Capsule Pill Bar */}
              <div
                className={`w-full max-w-[58px] rounded-t-full rounded-b-2xl transition-all duration-500 relative overflow-hidden ${
                  isLeader
                    ? 'bg-gradient-to-t from-winsor-900 via-winsor-600 to-sky-400 shadow-[0_0_25px_rgba(37,99,235,0.4)] border border-sky-300/40'
                    : isHovered
                    ? 'bg-gradient-to-t from-slate-900 via-winsor-900 to-winsor-500 border border-winsor-500/40'
                    : 'bg-gradient-to-t from-[#0e121d] via-[#151c2d] to-[#202a42] border border-white/[0.05]'
                }`}
                style={{ height: `${bar.heightPercent}%` }}
              >
                {/* Gloss highlight reflection inside capsule */}
                <div className="absolute inset-x-1 top-1 h-6 rounded-t-full bg-white/15 pointer-events-none" />
              </div>

              {/* Label */}
              <span className="mt-2 text-[11px] font-mono text-slate-400 group-hover:text-white transition-colors">
                {bar.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Bottom Insights row */}
      <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          <TrendingUp className="w-3.5 h-3.5 text-winsor-400" />
          <span className="text-[11px]">
            Leading Driver: <strong className="text-white">Quality / ROE Expansion</strong>
          </span>
        </div>
        <div className="flex items-center space-x-1 text-winsor-400 hover:text-winsor-300 cursor-pointer font-medium text-[11px]">
          <span>Detailed Factor Audit</span>
          <ArrowUpRight className="w-3 h-3" />
        </div>
      </div>
    </div>
  );
};
