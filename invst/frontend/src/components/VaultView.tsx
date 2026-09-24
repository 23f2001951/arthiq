import React, { useState, useEffect } from 'react';
import { fetchDashboard } from '../api/client';
import { DashboardResponse } from '../types/api';
import { ShieldCheck } from 'lucide-react';

export const VaultView: React.FC = () => {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard()
      .then((data) => setDashboard(data))
      .catch((err) => console.error('Vault error:', err))
      .finally(() => setLoading(false));
  }, []);

  const formatSector = (s: string) =>
    s ? s.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()) : 'General';

  if (loading || !dashboard) {
    return (
      <div className="glass-card p-12 text-center text-slate-400 font-mono text-xs animate-pulse">
        LOADING VAULT ALLOCATIONS &amp; RISK CAPS...
      </div>
    );
  }

  const sectorEntries = Object.entries(dashboard.sector_allocations);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-[#080b13] border border-emerald-500/20 shadow-2xl relative overflow-hidden mesh-glow-emerald">
        <div className="absolute inset-0 bg-dot-grid opacity-20 pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                <ShieldCheck className="w-4 h-4" />
              </span>
              <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-widest">
                Portfolio Allocation &amp; Funds Vault
              </span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
              Vault: Diversified Asset Architecture
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Understand your portfolio exposures — monitor inverse-volatility weights, track sector concentration barriers, and audit hard risk caps.
            </p>
          </div>

          <div className="flex items-center space-x-3 bg-black/40 p-3 rounded-2xl border border-white/[0.08] shrink-0 font-mono">
            <div className="text-right">
              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Active Holdings</span>
              <span className="text-sm font-bold text-white">{dashboard.holdings.length} Positions</span>
            </div>
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
        </div>
      </div>

      {/* 2-Column Bento: Donut Ring Exposure & Constraints */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sector Exposure Donut Card (Inspired by Image 2 Vault Card) */}
        <div className="glass-card p-6 sm:p-8 relative overflow-hidden flex flex-col justify-between">
          <div className="absolute inset-0 bg-dot-grid opacity-15 pointer-events-none" />
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
                Sector Diversification Split
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                MAX SECTOR CAP: 40.0%
              </span>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-6 mt-4">
              {/* Sector Bars List */}
              <div className="space-y-3 w-full sm:w-1/2 font-mono text-xs">
                {sectorEntries.map(([sec, weight], idx) => {
                  const colors = ['bg-sky-400', 'bg-yellow-400', 'bg-emerald-400', 'bg-purple-400', 'bg-amber-400'];
                  const color = colors[idx % colors.length];
                  const pct = (weight * 100).toFixed(1);
                  return (
                    <div key={sec} className="space-y-1">
                      <div className="flex items-center justify-between text-slate-300">
                        <span className="flex items-center space-x-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
                          <span className="text-xs font-sans text-slate-200">{formatSector(sec)}</span>
                        </span>
                        <span className="font-bold text-white">{pct}%</span>
                      </div>
                      <div className="w-full bg-[#131726] h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`${color} h-full rounded-full transition-all duration-500`}
                          style={{ width: `${Math.min(weight * 250, 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Graphic Donut Mockup */}
              <div className="relative w-36 h-36 flex items-center justify-center shrink-0">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                  <circle cx="18" cy="18" r="14" fill="none" stroke="#121622" strokeWidth="4.5" />
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="4.5"
                    strokeDasharray="30 100"
                    strokeLinecap="round"
                  />
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="#facc15"
                    strokeWidth="4.5"
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
                    strokeWidth="4.5"
                    strokeDasharray="22 100"
                    strokeDashoffset="-60"
                    strokeLinecap="round"
                  />
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="#a855f7"
                    strokeWidth="4.5"
                    strokeDasharray="14 100"
                    strokeDashoffset="-85"
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-sm font-mono font-black text-white">&lt;25%</span>
                  <span className="text-[8px] font-mono text-slate-400 uppercase">Single Stock</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-white/[0.06] text-[11px] text-slate-500">
            Sector limits prevent idiosyncratic industry contagion across shifting interest rate cycles.
          </div>
        </div>

        {/* Risk Limits & Rebalance Rules */}
        <div className="space-y-4">
          <div className="glass-card p-6">
            <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider block mb-3">
              Institutional Risk Constraints
            </span>
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
                <div>
                  <span className="font-bold text-white block">Maximum Single Stock Weight</span>
                  <span className="text-[10px] text-slate-500">Hard stop to avoid concentration risk</span>
                </div>
                <span className="font-bold text-amber-400 text-sm">25.0%</span>
              </div>

              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
                <div>
                  <span className="font-bold text-white block">Maximum Sector Exposure</span>
                  <span className="text-[10px] text-slate-500">Industry diversification rule</span>
                </div>
                <span className="font-bold text-sky-400 text-sm">40.0%</span>
              </div>

              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
                <div>
                  <span className="font-bold text-white block">Rebalancing Cadence</span>
                  <span className="text-[10px] text-slate-500">Quarterly out-of-sample execution</span>
                </div>
                <span className="font-bold text-emerald-400 text-sm">Quarterly (Mar/Jun/Sep/Dec)</span>
              </div>
            </div>
          </div>

          <div className="glass-card p-6">
            <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider block mb-2">
              Execution Cost Buffers
            </span>
            <div className="grid grid-cols-3 gap-2 text-center font-mono text-xs">
              <div className="bg-white/[0.02] p-2 rounded-xl">
                <span className="text-[10px] text-slate-500 block">Buy Bps</span>
                <span className="font-bold text-slate-200">30 bps</span>
              </div>
              <div className="bg-white/[0.02] p-2 rounded-xl">
                <span className="text-[10px] text-slate-500 block">Sell Bps</span>
                <span className="font-bold text-slate-200">20 bps</span>
              </div>
              <div className="bg-white/[0.02] p-2 rounded-xl">
                <span className="text-[10px] text-slate-500 block">Slippage</span>
                <span className="font-bold text-slate-200">5 bps</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Target Holdings Table */}
      <div className="glass-card p-6 overflow-hidden">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-white">Active Vault Allocations</h3>
            <p className="text-xs text-slate-400">Exact weights and target share units in current rebalance run</p>
          </div>
          <span className="text-xs font-mono text-slate-400">As-Of: {dashboard.latest_asof || 'Live'}</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-slate-500 uppercase text-[10px]">
                <th className="py-2.5 px-3">Symbol</th>
                <th className="py-2.5 px-3">Sector</th>
                <th className="py-2.5 px-3">Target Weight</th>
                <th className="py-2.5 px-3">Target Shares</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {dashboard.holdings.map((h) => (
                <tr key={h.symbol} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 px-3 font-bold text-white">{h.symbol}</td>
                  <td className="py-3 px-3 font-sans text-slate-400">{formatSector(h.sector)}</td>
                  <td className="py-3 px-3 font-bold text-amber-400">{(h.target_weight * 100).toFixed(1)}%</td>
                  <td className="py-3 px-3 text-slate-300">{h.shares_target || '—'}</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      {h.action}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-slate-400">
                    {h.executed ? 'Executed' : 'Pending'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
