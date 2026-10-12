import React, { useState, useMemo } from 'react';
import { Sparkles, TrendingUp, ChevronRight } from 'lucide-react';
import { MainPortfolioPositionItem, HoldingItem } from '../types/api';

interface CapsuleBarChartProps {
  positions?: MainPortfolioPositionItem[];
  modelHoldings?: HoldingItem[];
  totalValue?: number;
  totalPnl?: number;
  totalPnlPct?: number;
  portfolioName?: string;
  onSelectStock?: (symbol: string) => void;
}

export const CapsuleBarChart: React.FC<CapsuleBarChartProps> = ({
  positions = [],
  modelHoldings = [],
  totalValue = 0,
  totalPnl = 0,
  totalPnlPct = 0,
  portfolioName = 'Main Portfolio',
  onSelectStock,
}) => {
  const [activeTab, setActiveTab] = useState<'weight' | 'pnl' | 'horizon'>('weight');
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const hasRealHoldings = positions.length > 0;

  // Build unified item list from either real positions or model holdings
  const items = useMemo(() => {
    if (hasRealHoldings) {
      return positions.map((p) => ({
        symbol: p.symbol,
        sector: (p.sector || 'General').replace(/_/g, ' '),
        weight: p.weight_pct || 0,
        currentValue: p.current_value || 0,
        shares: p.shares || 0,
        buyPrice: p.buy_price || 0,
        currentPrice: p.current_price || 0,
        pnl: p.unrealized_pnl || 0,
        pnlPct: p.unrealized_pnl_pct || 0,
        expected12m: p.expected_return_12m ?? null,
        action: p.action_badge || 'HOLD',
        rationale: p.action_rationale || '',
      }));
    }

    // Fallback to Algorithmic Model Holdings
    if (modelHoldings.length > 0) {
      return modelHoldings.map((m) => ({
        symbol: m.symbol,
        sector: (m.sector || 'General').replace(/_/g, ' '),
        weight: m.target_weight * 100,
        currentValue: 0,
        shares: m.shares_target || 0,
        buyPrice: 0,
        currentPrice: 0,
        pnl: 0,
        pnlPct: null,
        expected12m: null,
        action: m.action || 'BUY',
        rationale: '',
      }));
    }

    return [];
  }, [positions, modelHoldings, hasRealHoldings]);

  // Determine bar heights based on active view mode
  const barsData = useMemo(() => {
    let maxVal = 1;
    if (activeTab === 'weight') {
      maxVal = Math.max(...items.map((i) => i.weight), 25.0);
    } else if (activeTab === 'pnl') {
      maxVal = Math.max(...items.map((i) => Math.abs(i.pnlPct || 0)), 1);
    } else {
      maxVal = Math.max(...items.map((i) => i.expected12m || 0), 1);
    }

    return items.map((item) => {
      let rawVal = 0;
      let displayVal = '';
      let isPositive = true;

      if (activeTab === 'weight') {
        rawVal = item.weight;
        displayVal = `${item.weight.toFixed(1)}%`;
        isPositive = item.weight <= 25.0; // Over 25% is warning
      } else if (activeTab === 'pnl') {
        rawVal = item.pnlPct || 0;
        displayVal = `${rawVal >= 0 ? '+' : ''}${rawVal.toFixed(1)}%`;
        isPositive = rawVal >= 0;
      } else {
        rawVal = item.expected12m || 0;
        displayVal = `${rawVal >= 0 ? '+' : ''}${rawVal.toFixed(1)}%`;
        isPositive = true;
      }

      // Height between 25% and 94%
      const heightPercent = Math.min(96, Math.max(22, (Math.abs(rawVal) / maxVal) * 88));

      return {
        ...item,
        rawVal,
        displayVal,
        heightPercent,
        isPositive,
      };
    });
  }, [items, activeTab]);

  // Top position
  const topItem = useMemo(() => {
    if (barsData.length === 0) return null;
    return [...barsData].sort((a, b) => b.rawVal - a.rawVal)[0];
  }, [barsData]);

  const availableTabs = [
    { id: 'weight' as const, label: 'Weight %', available: items.length > 0 },
    { id: 'pnl' as const, label: 'P&L Return', available: hasRealHoldings },
    { id: 'horizon' as const, label: '12M Outlook', available: items.some((item) => item.expected12m !== null) },
  ].filter((tab) => tab.available);

  React.useEffect(() => {
    if (!availableTabs.some((tab) => tab.id === activeTab) && availableTabs.length > 0) {
      setActiveTab(availableTabs[0].id);
    }
  }, [activeTab, availableTabs]);

  return (
    <div className="capsule-chart glass-panel p-6 rounded-3xl relative overflow-hidden flex flex-col justify-between space-y-4">
      {/* Background ambient glow */}
      <div className="absolute top-0 left-1/3 w-64 h-64 bg-sky-500/5 blur-3xl pointer-events-none" />

      {/* Top Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 relative z-10">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-bold tracking-wider text-sky-400 uppercase flex items-center font-mono">
              <Sparkles className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
              Stock Weight &amp; Capital Attribution
            </span>
            <span className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-white/[0.04] text-slate-400 border border-white/[0.08]">
              {hasRealHoldings ? `${portfolioName} • Portfolio snapshot` : 'Algorithmic target weights'}
            </span>
          </div>

          <div className="flex items-baseline space-x-2 mt-1">
            <h2 className="text-2xl sm:text-3xl font-black font-mono text-white tracking-tight">
              {hasRealHoldings && totalValue > 0
                ? `₹${Math.round(totalValue).toLocaleString('en-IN')}`
                : `${items.length} Positions`}
              {hasRealHoldings && (
                <span className={`text-xs sm:text-sm font-bold ml-2.5 font-mono ${totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {totalPnl >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}% ({totalPnl >= 0 ? '+' : ''}₹{Math.round(totalPnl).toLocaleString('en-IN')})
                </span>
              )}
            </h2>
          </div>
        </div>

        {/* View Mode Pills */}
        {availableTabs.length > 1 && <div className="flex items-center space-x-2">
          <div className="flex bg-[#05070d] p-1 rounded-xl border border-white/[0.08] shadow-inner text-xs font-mono">
            {availableTabs.map((tab) => (
              <button key={tab.id} onClick={() => { setActiveTab(tab.id); setHoveredIdx(null); }} className={`px-3 py-1 rounded-lg font-bold transition-all duration-200 cursor-pointer ${activeTab === tab.id ? 'bg-winsor-700 text-white border border-winsor-500/50' : 'text-slate-400 hover:text-white'}`}>
                {tab.label}
              </button>
            ))}
          </div>
        </div>}
      </div>

      {/* Chart Canvas Area with Real Stock Tickers */}
      {barsData.length > 0 ? <div className="relative h-64 mt-2 w-full flex items-end justify-between px-2 sm:px-4 pt-10 select-none">
        {/* Horizontal guide lines */}
        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20">
          <div className="border-b border-dashed border-slate-600 flex justify-between text-[10px] text-slate-400 font-mono">
            <span>{activeTab === 'weight' ? 'Allocation scale' : activeTab === 'pnl' ? 'Return scale' : 'Expected return scale'}</span>
          </div>
          <div className="border-b border-dashed border-slate-600 flex justify-between text-[10px] text-slate-400 font-mono">
            <span>{activeTab === 'weight' ? 'Allocation' : activeTab === 'pnl' ? 'Return' : 'Expected return'}</span>
          </div>
          <div className="border-b border-dashed border-slate-600 flex justify-between text-[10px] text-slate-400 font-mono">
            <span>Baseline (0%)</span>
          </div>
        </div>

        {/* Real Stock Capsule Pillar Bars */}
        {barsData.map((bar, idx) => {
          const isHovered = hoveredIdx === idx;
          const isLeader = topItem?.symbol === bar.symbol;
          const isCapWarning = activeTab === 'weight' && bar.weight > 25.0;

          return (
            <div
              key={bar.symbol}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              onClick={() => onSelectStock && onSelectStock(bar.symbol)}
              className="relative flex flex-col items-center justify-end h-full z-10 group cursor-pointer"
              style={{ width: `${100 / barsData.length - 2.5}%` }}
            >
              {/* Detailed Real Stock Tooltip on Hover */}
              {isHovered && (
                <div className="absolute -top-24 z-30 px-3.5 py-2.5 rounded-2xl bg-[#070a14] border border-sky-400/60 shadow-2xl shadow-black/90 whitespace-nowrap text-left animate-fadeInUp min-w-[170px]">
                  <div className="flex items-center justify-between gap-2 border-b border-white/[0.08] pb-1.5">
                    <span className="font-mono font-black text-sm text-white">{bar.symbol}</span>
                    <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-white/[0.05] text-slate-300">
                      {bar.action}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 truncate mt-1">
                    {bar.sector}
                  </div>
                  <div className="mt-1.5 space-y-0.5 font-mono text-xs">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-slate-400">Weight:</span>
                      <span className={`font-bold ${isCapWarning ? 'text-rose-400' : 'text-sky-300'}`}>
                        {bar.weight.toFixed(1)}% {isCapWarning ? '(>25% Cap)' : ''}
                      </span>
                    </div>
                    {hasRealHoldings && (
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">Value:</span>
                        <span className="font-bold text-white">
                          ₹{Math.round(bar.currentValue).toLocaleString('en-IN')}
                        </span>
                      </div>
                    )}
                    {bar.pnlPct !== null && <div className="flex justify-between text-[11px]">
                      <span className="text-slate-400">P&amp;L Return:</span>
                      <span className={`font-bold ${bar.pnlPct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {bar.pnlPct >= 0 ? '+' : ''}{bar.pnlPct.toFixed(1)}%
                      </span>
                    </div>}
                    {bar.expected12m !== null && <div className="flex justify-between text-[11px]">
                      <span className="text-slate-400">12M Expected Return:</span>
                      <span className="font-bold text-emerald-400">
                        +{bar.expected12m.toFixed(1)}%
                      </span>
                    </div>}
                  </div>
                </div>
              )}

              {/* Glowing Beacon Dot on Top of Pillar */}
              <div
                className={`w-3.5 h-3.5 rounded-full mb-1.5 transition-all duration-300 flex items-center justify-center ${
                  `capsule-chart__beacon ${isCapWarning ? 'is-warning' : isLeader ? 'is-leader' : isHovered ? 'is-hovered' : ''}`
                }`}
              >
                <div className="w-1.5 h-1.5 rounded-full bg-white" />
              </div>

              {/* Domed Capsule Pillar Bar */}
              <div
                className={`capsule-chart__bar w-full max-w-[52px] rounded-t-full rounded-b-2xl transition-all duration-700 ease-out relative overflow-hidden ${isCapWarning ? 'is-warning' : isLeader ? 'is-leader' : ''} ${
                  isCapWarning
                    ? 'bg-gradient-to-t from-rose-950 via-rose-700 to-rose-400 shadow-[0_0_20px_rgba(244,63,94,0.4)] border border-rose-300/40'
                    : isLeader
                    ? 'bg-gradient-to-t from-winsor-950 via-winsor-600 to-sky-400 shadow-[0_0_25px_rgba(37,99,235,0.4)] border border-sky-300/50'
                    : isHovered
                    ? 'bg-gradient-to-t from-slate-900 via-winsor-900 to-winsor-500 border border-winsor-500/50'
                    : 'bg-gradient-to-t from-[#0b0e17] via-[#131a2b] to-[#1c263c] border border-white/[0.06]'
                }`}
                style={{ height: `${bar.heightPercent}%` }}
              >
                {/* Gloss highlight reflection inside capsule */}
                <div className="absolute inset-x-1 top-1 h-5 rounded-t-full bg-white/20 pointer-events-none" />
              </div>

              {/* Real Ticker Label */}
              <span className={`mt-2 text-xs font-mono font-black tracking-tight transition-colors ${
                isCapWarning ? 'text-rose-400' : isLeader ? 'text-sky-300' : isHovered ? 'text-white' : 'text-slate-400'
              }`}>
                {bar.symbol}
              </span>

              {/* Value Sub-label */}
              <span className="text-[10px] font-mono text-slate-500 group-hover:text-slate-300">
                {bar.displayVal}
              </span>
            </div>
          );
        })}
      </div> : (
        <div className="min-h-64 mt-2 flex items-center justify-center rounded-2xl border border-dashed border-white/10 text-sm text-slate-400">
          No holdings or target weights are available for this chart.
        </div>
      )}

      {/* Bottom Insights Row */}
      <div className="pt-3 border-t border-white/[0.08] flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 relative z-10">
        <div className="flex items-center space-x-2">
          <TrendingUp className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="text-[11px]">
            {topItem ? (
              <>
                {hasRealHoldings ? 'Largest allocation' : 'Largest target weight'}: <strong className="text-white font-mono">{topItem.symbol}</strong> ({topItem.weight.toFixed(1)}%)
              </>
            ) : 'No position data available'}
          </span>
        </div>

        <div className="flex items-center space-x-1 text-sky-400 hover:text-sky-300 cursor-pointer font-bold text-[11px] font-mono transition-colors">
          <span>Click any stock to inspect</span>
          <ChevronRight className="w-3 h-3" />
        </div>
      </div>
    </div>
  );
};

export default CapsuleBarChart;
