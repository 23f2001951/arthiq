import React, { useState } from 'react';
import { StockRecommendationItem } from '../types/api';
import { ArrowUpDown, Sparkles } from 'lucide-react';

interface FactorMatrixViewProps {
  stocks: StockRecommendationItem[];
}

export const FactorMatrixView: React.FC<FactorMatrixViewProps> = ({ stocks }) => {
  const [sortField, setSortField] = useState<'arth' | 'prob' | 'composite' | 'quality' | 'valuation' | 'risk'>('arth');

  const sortedStocks = [...stocks].sort((a, b) => {
    if (sortField === 'arth') return (b.arth_score ?? b.composite_score * 100) - (a.arth_score ?? a.composite_score * 100);
    if (sortField === 'prob') return (b.p_outperform ?? 0.5) - (a.p_outperform ?? 0.5);
    if (sortField === 'quality') return b.quality_score - a.quality_score;
    if (sortField === 'valuation') return b.valuation_score - a.valuation_score;
    if (sortField === 'risk') return b.risk_score - a.risk_score;
    return b.composite_score - a.composite_score;
  });

  return (
    <div className="glass-card rounded-3xl overflow-hidden shadow-2xl border border-white/[0.08]">
      {/* Header Bar */}
      <div className="p-5 border-b border-white/[0.06] flex flex-wrap items-center justify-between gap-3 bg-[#07090f]/70">
        <div>
          <h3 className="text-sm font-black uppercase tracking-wider text-white flex items-center">
            <Sparkles className="w-4 h-4 mr-2 text-sky-400" />
            Cross-Sectional Factor & Alpha Comparison Matrix
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Institutional ArthScores, calibrated outperformance probabilities, and factor percentiles
          </p>
        </div>

        {/* Quick Sort Tabs with Arth IQ Active State */}
        <div className="flex items-center space-x-1.5 text-xs bg-[#05070d] p-1.5 rounded-2xl border border-white/[0.08]">
          <span className="text-slate-500 px-2 py-0.5 flex items-center font-mono text-[11px]">
            <ArrowUpDown className="w-3 h-3 mr-1 text-sky-400" /> Sort:
          </span>
          {(['arth', 'prob', 'composite', 'quality', 'valuation', 'risk'] as const).map((field) => (
            <button
              key={field}
              onClick={() => setSortField(field)}
              className={`px-3 py-1 rounded-xl capitalize font-bold transition-all text-xs ${
                sortField === field
                  ? 'bg-gradient-to-r from-winsor-600 to-sky-500 text-white shadow-md shadow-winsor-500/25 font-black'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {field === 'arth' ? 'ArthScore' : field === 'prob' ? 'P(Alpha)' : field}
            </button>
          ))}
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#080b13] text-slate-400 font-bold uppercase tracking-wider border-b border-white/[0.06]">
            <tr>
              <th className="py-3.5 px-4">Rank & Symbol</th>
              <th className="py-3.5 px-4">Sector</th>
              <th className="py-3.5 px-4 text-center">ArthScore</th>
              <th className="py-3.5 px-4 text-center">P(Alpha &gt; 0)</th>
              <th className="py-3.5 px-4 w-40">Quality (40%)</th>
              <th className="py-3.5 px-4 w-40">Valuation (30%)</th>
              <th className="py-3.5 px-4 w-40">Risk (30%)</th>
              <th className="py-3.5 px-4 text-right">Target Weight</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04] font-medium text-slate-200">
            {sortedStocks.map((stock, idx) => {
              const qPct = stock.quality_score * 100;
              const vPct = stock.valuation_score * 100;
              const rPct = stock.risk_score * 100;
              const cPct = stock.composite_score * 100;

              return (
                <tr
                  key={stock.symbol}
                  className="hover:bg-winsor-950/20 transition-colors group"
                >
                  {/* Rank & Symbol */}
                  <td className="py-3.5 px-4 font-mono">
                    <div className="flex items-center space-x-2.5">
                      <span className="w-6 h-6 rounded-lg bg-[#0c101a] border border-white/[0.08] text-sky-300 font-bold flex items-center justify-center text-xs">
                        {idx + 1}
                      </span>
                      <span className="font-black text-sm text-white group-hover:text-sky-300 transition-colors">
                        {stock.symbol}
                      </span>
                    </div>
                  </td>

                  {/* Sector */}
                  <td className="py-3.5 px-4 capitalize text-slate-400">
                    {stock.sector.replace(/_/g, ' ')}
                  </td>

                  {/* ArthScore */}
                  <td className="py-3.5 px-4 text-center font-mono font-black">
                    <span className="px-2.5 py-1 rounded-lg bg-[#0e1322] text-sky-300 border border-sky-500/30 text-xs shadow-sm">
                      {(stock.arth_score ?? cPct).toFixed(1)}
                    </span>
                  </td>

                  {/* P(Alpha > 0) Probability */}
                  <td className="py-3.5 px-4 text-center font-mono font-black">
                    <span className={`px-2 py-0.5 rounded-lg text-xs border ${
                      (stock.p_outperform ?? 0.5) >= 0.70
                        ? 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40'
                        : (stock.p_outperform ?? 0.5) >= 0.55
                        ? 'bg-sky-950/70 text-sky-300 border-sky-500/40'
                        : 'bg-[#090d16] text-slate-400 border-white/[0.08]'
                    }`}>
                      {Math.round((stock.p_outperform ?? 0.5) * 100)}%
                    </span>
                  </td>

                  {/* Quality Bar */}
                  <td className="py-3.5 px-4">
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px] font-mono">
                        <span className="text-emerald-400 font-bold">{qPct.toFixed(1)}</span>
                        <span className="text-slate-500">
                          ROCE: {stock.quality_metrics?.roce !== undefined && stock.quality_metrics.roce !== null ? `${stock.quality_metrics.roce.toFixed(1)}%` : '—'}
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-[#05070d] rounded-full overflow-hidden border border-white/[0.06]">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-teal-400"
                          style={{ width: `${Math.min(100, Math.max(5, qPct))}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Valuation Bar */}
                  <td className="py-3.5 px-4">
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px] font-mono">
                        <span className="text-sky-400 font-bold">{vPct.toFixed(1)}</span>
                        <span className="text-slate-500">
                          P/E: {stock.valuation_metrics?.pe_ratio !== undefined && stock.valuation_metrics.pe_ratio !== null ? stock.valuation_metrics.pe_ratio.toFixed(1) : '—'}
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-[#05070d] rounded-full overflow-hidden border border-white/[0.06]">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-winsor-600 to-sky-400"
                          style={{ width: `${Math.min(100, Math.max(5, vPct))}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Risk Bar */}
                  <td className="py-3.5 px-4">
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px] font-mono">
                        <span className="text-indigo-400 font-bold">{rPct.toFixed(1)}</span>
                        <span className="text-slate-500">
                          D/E: {stock.risk_metrics?.debt_to_equity !== undefined && stock.risk_metrics.debt_to_equity !== null ? stock.risk_metrics.debt_to_equity.toFixed(2) : '—'}
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-[#05070d] rounded-full overflow-hidden border border-white/[0.06]">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-purple-400"
                          style={{ width: `${Math.min(100, Math.max(5, rPct))}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Target Weight */}
                  <td className="py-3.5 px-4 text-right font-mono font-black text-emerald-400 text-sm">
                    {(stock.target_weight * 100).toFixed(2)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
