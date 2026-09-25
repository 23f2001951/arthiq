import React, { useEffect, useState } from 'react';
import { fetchDashboard } from '../api/client';
import { DashboardResponse } from '../types/api';
import { KPICard } from '../components/KPICard';
import { SectorAllocation } from '../components/SectorAllocation';
import { TrendSparkline } from '../components/TrendSparkline';
import { CapsuleBarChart } from '../components/CapsuleBarChart';
import { MarketRegimeArcGauge } from '../components/MarketRegimeArcGauge';
import { TradeOrderBlotter } from '../components/TradeOrderBlotter';
import { QuickSizingConverter } from '../components/QuickSizingConverter';
import { HeroClarityBanner } from '../components/HeroClarityBanner';
import { FiveToolsBento } from '../components/FiveToolsBento';
import { HowItWorksBento } from '../components/HowItWorksBento';
import {
  Wallet,
  PieChart,
  RefreshCw,
  TrendingUp,
  Activity,
  ArrowUpRight,
} from 'lucide-react';

interface DashboardViewProps {
  onNavigateTab?: (tabId: string, subTabId?: string) => void;
}

const safeNum = (val: any, fallback: number = 0): number => {
  if (val === null || val === undefined || isNaN(Number(val))) return fallback;
  return Number(val);
};

const safeToLocale = (val: any, decimals?: number): string => {
  const num = safeNum(val, 0);
  if (decimals !== undefined) {
    return num.toLocaleString('en-IN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }
  return num.toLocaleString('en-IN');
};

const safeToFixed = (val: any, decimals: number = 2): string => {
  return safeNum(val, 0).toFixed(decimals);
};

class DashboardErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Dashboard caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 bg-[#12080a] border border-rose-800/60 rounded-3xl text-rose-200 space-y-4">
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 rounded-full bg-rose-500 animate-ping" />
            <h3 className="text-lg font-bold text-white">Dashboard Encountered an Issue</h3>
          </div>
          <p className="text-xs text-rose-300 font-mono">
            {this.state.error?.message || 'A data display error occurred while rendering the dashboard.'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="px-4 py-2 bg-rose-900/60 hover:bg-rose-800 border border-rose-700 rounded-xl text-xs font-bold text-white transition-colors cursor-pointer"
          >
            Reload Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const DashboardViewInner: React.FC<DashboardViewProps> = ({ onNavigateTab }) => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTableTab, setActiveTableTab] = useState<'main' | 'model'>('main');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDashboard();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load portfolio dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-72 text-slate-400 glass-card rounded-3xl border border-white/[0.06]">
        <div className="w-12 h-12 rounded-full border-2 border-winsor-500/20 border-t-winsor-500 animate-spin mb-4" />
        <span className="font-semibold text-slate-200">Connecting to Arth IQ Engine...</span>
        <span className="text-xs text-slate-500 mt-1 font-mono">Loading portfolio & point-in-time state</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-[#160b0d] border border-rose-900/60 rounded-3xl text-rose-300 flex items-center justify-between">
        <div>
          <h4 className="font-bold text-rose-200">Quant Stream Disconnected</h4>
          <p className="text-xs mt-1 text-slate-400">{error || 'No portfolio data found.'}</p>
        </div>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-rose-900/40 hover:bg-rose-800/60 border border-rose-700/50 rounded-xl text-xs font-bold text-white transition-colors cursor-pointer"
        >
          Re-establish Link
        </button>
      </div>
    );
  }

  const mainPort = data.main_portfolio;
  const macro = data.macro_pulse;
  const positions = mainPort?.positions || [];
  const hasMainHoldings = Boolean(mainPort && (mainPort.holdings_count > 0 || positions.length > 0));
  const modelHoldings = data.holdings || [];

  return (
    <div className="space-y-10">
      {/* 1. Hero Clarity Banner */}
      <HeroClarityBanner
        onExploreTools={() => onNavigateTab && onNavigateTab('recommendations')}
        onLaunchBacktest={() => onNavigateTab && onNavigateTab('backtest')}
      />

      {/* 2. Top Header & Fast Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <div>
          <div className="flex items-center space-x-2.5">
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
              {mainPort?.portfolio_name || 'Main Portfolio'} Dashboard
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-winsor-950 text-winsor-400 border border-winsor-800/60 font-mono flex items-center">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
              LIVE ENGINE
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real portfolio status & risk parity constraints as of{' '}
            <span className="text-winsor-400 font-mono font-bold">
              {data.latest_asof || new Date().toISOString().split('T')[0]}
            </span>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {onNavigateTab && (
            <button
              onClick={() => onNavigateTab('portfolio')}
              className="flex items-center space-x-1.5 px-4 py-2 bg-[#0c101a] hover:bg-[#121827] border border-winsor-500/30 rounded-xl text-xs font-bold text-winsor-400 transition-all cursor-pointer"
            >
              <span>Manage Holdings</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            onClick={loadData}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-[#0c101a] hover:bg-[#121827] border border-white/[0.08] rounded-xl text-xs font-bold text-slate-300 transition-all shadow-sm cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Critical Redline & Sector Alerts */}
      {mainPort?.critical_redline_alerts && mainPort.critical_redline_alerts.length > 0 && (
        <div className="p-4 bg-rose-950/40 border border-rose-800/60 rounded-2xl text-rose-200">
          <div className="flex items-center space-x-2 text-xs font-bold text-rose-400 uppercase tracking-wider mb-1">
            <span>🚨 Critical Redline Alert on Active Holdings</span>
          </div>
          <ul className="text-xs space-y-1 list-disc list-inside text-rose-300/90 font-mono">
            {mainPort.critical_redline_alerts.map((a, idx) => (
              <li key={idx}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {mainPort?.sector_warnings && mainPort.sector_warnings.length > 0 && (
        <div className="p-4 bg-amber-950/40 border border-amber-800/60 rounded-2xl text-amber-200">
          <div className="flex items-center space-x-2 text-xs font-bold text-amber-400 uppercase tracking-wider mb-1">
            <span>⚠️ Sector Concentration Warning (&gt; 40% Cap)</span>
          </div>
          <ul className="text-xs space-y-1 list-disc list-inside text-amber-300/90 font-mono">
            {mainPort.sector_warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 3. Top 4 Institutional KPI Metric Cards (Real Values) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Total Portfolio Value"
          value={hasMainHoldings ? `₹${safeToLocale(Math.round(safeNum(mainPort?.total_current_value)))}` : '₹0'}
          subtitle={hasMainHoldings ? `Total Invested: ₹${safeToLocale(Math.round(safeNum(mainPort?.total_invested)))}` : 'No active holdings'}
          delta={hasMainHoldings ? `${safeNum(mainPort?.total_unrealized_pnl_pct) >= 0 ? '+' : ''}${safeToFixed(mainPort?.total_unrealized_pnl_pct, 2)}% Return` : '0.00%'}
          deltaPositive={hasMainHoldings ? safeNum(mainPort?.total_unrealized_pnl) >= 0 : true}
          icon={Wallet}
          variant="emerald"
          sparkline={true}
        />
        <KPICard
          label="Portfolio Health Score"
          value={hasMainHoldings ? `${safeToFixed(mainPort?.overall_health_score, 1)}/100` : 'N/A'}
          subtitle={hasMainHoldings ? `Grade: ${mainPort?.overall_health_grade || 'NEUTRAL'}` : 'Audit pending'}
          delta={hasMainHoldings ? `Quality: ${safeToFixed(mainPort?.weighted_business_score, 0)} | Val: ${safeToFixed(mainPort?.weighted_valuation_score, 0)}` : 'No score'}
          deltaPositive={hasMainHoldings ? safeNum(mainPort?.overall_health_score) >= 60 : true}
          icon={TrendingUp}
          variant="winsor"
          sparkline={true}
        />
        <KPICard
          label="NSE Market Volatility"
          value={safeToFixed(macro?.india_vix ?? 14.5, 2)}
          subtitle={macro?.regime_description || 'India VIX Regime'}
          delta={macro?.regime ? `${macro.regime} Regime` : 'NEUTRAL'}
          deltaPositive={macro?.regime !== 'HIGH_VOLATILITY'}
          icon={Activity}
          variant={macro?.regime === 'HIGH_VOLATILITY' ? 'amber' : 'info'}
          sparkline={false}
        />
        <KPICard
          label="Active Positions"
          value={hasMainHoldings ? `${mainPort?.holdings_count || positions.length} Stocks` : `${data.target_holdings || 8} Target`}
          subtitle={hasMainHoldings ? (mainPort?.portfolio_name || 'Main Portfolio') : 'Algorithmic 8-stock target'}
          delta={hasMainHoldings ? ((mainPort?.critical_redline_alerts?.length ?? 0) === 0 ? 'Zero Redlines' : `${mainPort?.critical_redline_alerts?.length} Redline Alert`) : 'Model Target'}
          deltaPositive={hasMainHoldings ? (mainPort?.critical_redline_alerts?.length ?? 0) === 0 : true}
          icon={PieChart}
          variant="purple"
          sparkline={true}
        />
      </div>

      {/* 4. Real Stock Weight & Performance Attribution + Market Regime Arc Dial */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <CapsuleBarChart
            positions={positions}
            modelHoldings={modelHoldings}
            totalValue={safeNum(mainPort?.total_current_value, 0)}
            totalPnl={safeNum(mainPort?.total_unrealized_pnl, 0)}
            totalPnlPct={safeNum(mainPort?.total_unrealized_pnl_pct, 0)}
            portfolioName={mainPort?.portfolio_name || 'Main Portfolio'}
            onSelectStock={() => {
              if (onNavigateTab) {
                onNavigateTab('analyzer');
              }
            }}
          />
        </div>
        <div className="lg:col-span-5">
          <MarketRegimeArcGauge
            score={hasMainHoldings ? Math.round(safeNum(mainPort?.overall_health_score, 75)) : 75}
            regime={macro?.regime || 'NEUTRAL'}
            vix={safeNum(macro?.india_vix, 14.5)}
          />
        </div>
      </div>

      {/* 5. Five Tools Bento */}
      <FiveToolsBento onSelectTool={(tool, subTool) => onNavigateTab && onNavigateTab(tool, subTool)} />

      {/* 6. How Arth IQ Works */}
      <HowItWorksBento />

      {/* 7. Order Execution Blotter + Sizing Converter */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <TradeOrderBlotter />
        </div>
        <div className="lg:col-span-5">
          <QuickSizingConverter symbol="RELIANCE" />
        </div>
      </div>

      {/* 8. Sector Exposure Distribution */}
      {((mainPort?.sector_exposures && Object.keys(mainPort.sector_exposures).length > 0) ||
        (data.sector_allocations && Object.keys(data.sector_allocations).length > 0)) && (
        <SectorAllocation
          sectors={
            mainPort?.sector_exposures && Object.keys(mainPort.sector_exposures).length > 0
              ? mainPort.sector_exposures
              : (data.sector_allocations || {})
          }
        />
      )}

      {/* 9. Portfolio Holdings & Model Table */}
      <div className="glass-panel overflow-hidden">
        <div className="p-5 border-b border-white/[0.08] flex flex-wrap items-center justify-between gap-4 bg-[#07090f]/70">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setActiveTableTab('main')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                activeTableTab === 'main'
                  ? 'bg-gradient-to-r from-winsor-700 to-sky-600 text-white border border-sky-400/50 shadow-[0_0_15px_rgba(37,99,235,0.4)]'
                  : 'text-slate-400 hover:text-white border border-transparent hover:bg-white/[0.04]'
              }`}
            >
              💼 Active Main Holdings ({positions.length})
            </button>
            <button
              onClick={() => setActiveTableTab('model')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                activeTableTab === 'model'
                  ? 'bg-gradient-to-r from-winsor-700 to-sky-600 text-white border border-sky-400/50 shadow-[0_0_15px_rgba(37,99,235,0.4)]'
                  : 'text-slate-400 hover:text-white border border-transparent hover:bg-white/[0.04]'
              }`}
            >
              🎯 Algorithmic Target Model ({modelHoldings.length})
            </button>
          </div>
          <span className="text-xs text-slate-400 font-mono font-bold">
            {activeTableTab === 'main'
              ? `${mainPort?.portfolio_name || 'Main Portfolio'} • Real Status`
              : 'Nifty 500 Strategy Model'}
          </span>
        </div>

        {activeTableTab === 'main' ? (
          positions.length === 0 ? (
            <div className="p-12 text-center text-sm text-slate-500">
              No active holdings found in Main Portfolio. Go to{' '}
              <button
                onClick={() => onNavigateTab && onNavigateTab('portfolio')}
                className="text-winsor-400 hover:underline font-bold cursor-pointer"
              >
                My Portfolio
              </button>{' '}
              to add or import holdings from your broker.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-[#080b13] text-slate-400 font-bold uppercase tracking-wider border-b border-white/[0.06]">
                  <tr>
                    <th className="py-3.5 px-4">Symbol</th>
                    <th className="py-3.5 px-4">Sector</th>
                    <th className="py-3.5 px-4 text-right">Shares</th>
                    <th className="py-3.5 px-4 text-right">Avg Price</th>
                    <th className="py-3.5 px-4 text-right">Current Price</th>
                    <th className="py-3.5 px-4 text-right">Current Value</th>
                    <th className="py-3.5 px-4 w-36">Weight</th>
                    <th className="py-3.5 px-4 text-right">Unrealized P&L</th>
                    <th className="py-3.5 px-4 text-center">12M Exp</th>
                    <th className="py-3.5 px-4 text-center">Action Advice</th>
                    <th className="py-3.5 px-4">Rationale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-medium">
                  {positions.map((p) => {
                    const pnl = safeNum(p.unrealized_pnl, 0);
                    const pnlPct = safeNum(p.unrealized_pnl_pct, 0);
                    const pnlSign = pnl >= 0 ? '+' : '';
                    const isPositive = pnl >= 0;
                    const weight = safeNum(p.weight_pct, 0);
                    const expReturn = safeNum(p.expected_return_12m, 0);
                    const sectorName = String(p.sector || 'General').replace(/_/g, ' ');

                    const action = p.action_badge || 'HOLD';
                    const isAccumulate = action.includes('ACCUMULATE') || action.includes('BUY');
                    const isTrim = action.includes('TRIM') || action.includes('REBALANCE') || action.includes('SELL');

                    return (
                      <tr
                        key={p.symbol}
                        className="hover:bg-sky-500/[0.04] transition-all duration-150 group border-l-2 border-transparent hover:border-sky-400"
                      >
                        <td className="py-3.5 px-4 font-black text-white font-mono text-sm tracking-tight group-hover:text-sky-300 transition-colors">
                          {p.symbol}
                        </td>
                        <td className="py-3.5 px-4 capitalize text-slate-400">
                          {sectorName}
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-200">
                          {safeToLocale(p.shares)}
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono text-slate-400">
                          ₹{safeToLocale(p.buy_price, 2)}
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono font-bold text-white">
                          ₹{safeToLocale(p.current_price, 2)}
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-200">
                          ₹{safeToLocale(Math.round(safeNum(p.current_value)))}
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="space-y-1">
                            <span className="text-[11px] font-mono font-bold text-winsor-400">{safeToFixed(weight, 1)}%</span>
                            <div className="w-full h-1.5 bg-[#05060a] rounded-full overflow-hidden border border-white/[0.06]">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-winsor-600 to-sky-400"
                                style={{ width: `${Math.min(100, (weight / 25) * 100)}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className={`py-3.5 px-4 text-right font-mono font-bold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {pnlSign}₹{safeToLocale(Math.round(pnl))}
                          <div className="text-[10px] opacity-80">{pnlSign}{safeToFixed(pnlPct, 2)}%</div>
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-200">
                          {expReturn >= 0 ? `+${safeToFixed(expReturn, 1)}%` : `${safeToFixed(expReturn, 1)}%`}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <span
                            className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border ${
                              isAccumulate
                                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30'
                                : isTrim
                                ? 'bg-rose-950/60 text-rose-300 border-rose-500/30'
                                : 'bg-sky-950/60 text-sky-300 border-sky-500/30'
                            }`}
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                isAccumulate ? 'bg-emerald-400 animate-pulse' : isTrim ? 'bg-rose-400' : 'bg-sky-400'
                              }`}
                            />
                            <span>{action}</span>
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-xs text-slate-400 max-w-xs truncate" title={p.action_rationale || ''}>
                          {p.action_rationale || '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )
        ) : (
          modelHoldings.length === 0 ? (
            <div className="p-12 text-center text-sm text-slate-500">
              No active holdings found in portfolio history. Run a backtest or quarterly rebalance to populate.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-[#080b13] text-slate-400 font-bold uppercase tracking-wider border-b border-white/[0.06]">
                  <tr>
                    <th className="py-3.5 px-4">Symbol</th>
                    <th className="py-3.5 px-4">Sector</th>
                    <th className="py-3.5 px-4">Action</th>
                    <th className="py-3.5 px-4 w-48">Target Weight</th>
                    <th className="py-3.5 px-4 text-center">Trend (30D)</th>
                    <th className="py-3.5 px-4 text-right">Target Shares</th>
                    <th className="py-3.5 px-4 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-medium">
                  {modelHoldings.map((h) => {
                    const weightPct = safeNum(h.target_weight, 0) * 100;
                    return (
                      <tr
                        key={h.symbol}
                        className="hover:bg-sky-500/[0.04] transition-all duration-150 group border-l-2 border-transparent hover:border-sky-400"
                      >
                        <td className="py-3.5 px-4 font-black text-white font-mono text-sm tracking-tight group-hover:text-sky-300 transition-colors">
                          {h.symbol}
                        </td>
                        <td className="py-3.5 px-4 capitalize text-slate-400">
                          {String(h.sector || 'General').replace(/_/g, ' ')}
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border ${
                              h.action === 'BUY'
                                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30'
                                : h.action === 'SELL'
                                ? 'bg-rose-950/60 text-rose-300 border-rose-500/30'
                                : 'bg-slate-800/60 text-slate-300 border-slate-700/50'
                            }`}
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                h.action === 'BUY' ? 'bg-emerald-400 animate-pulse' : h.action === 'SELL' ? 'bg-rose-400' : 'bg-slate-400'
                              }`}
                            />
                            <span>{h.action}</span>
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="space-y-1">
                            <div className="flex justify-between text-[11px] font-mono font-bold">
                              <span className="text-winsor-400">{safeToFixed(weightPct, 2)}%</span>
                              <span className="text-slate-500 font-normal">Cap 25%</span>
                            </div>
                            <div className="w-full h-1.5 bg-[#05060a] rounded-full overflow-hidden border border-white/[0.06]">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-winsor-600 to-sky-400"
                                style={{ width: `${Math.min(100, (weightPct / 25) * 100)}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <TrendSparkline
                            color="cyan"
                            isPositive={true}
                            width={75}
                            height={20}
                          />
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-200">
                          {h.shares_target !== null && h.shares_target !== undefined
                            ? safeToLocale(h.shares_target)
                            : '—'}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              h.executed
                                ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
                                : 'bg-amber-950/60 text-amber-400 border border-amber-800/50'
                            }`}
                          >
                            {h.executed ? 'Executed' : 'Pending'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    </div>
  );
};

export const DashboardView: React.FC<DashboardViewProps> = (props) => (
  <DashboardErrorBoundary>
    <DashboardViewInner {...props} />
  </DashboardErrorBoundary>
);
