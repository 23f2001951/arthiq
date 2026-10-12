import React, { useEffect, useState } from 'react';
import { fetchDashboard } from '../api/client';
import { DashboardResponse } from '../types/api';
import { KPICard } from '../components/KPICard';
import { SectorAllocation } from '../components/SectorAllocation';
import { CapsuleBarChart } from '../components/CapsuleBarChart';
import { MarketRegimeArcGauge } from '../components/MarketRegimeArcGauge';
import { useDailyMarketRefresh } from '../hooks/useDailyMarketRefresh';
import { MarketBenchmarkPanel } from '../components/MarketBenchmarkPanel';
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

  useDailyMarketRefresh(loadData);

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
    <div className="dashboard-workspace space-y-8">
      {/* Portfolio context and actions */}
      <div className="dashboard-workspace__header flex flex-wrap items-center justify-between gap-4 pt-2">
        <div>
          <div className="flex items-center space-x-2.5">
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
              Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}
            </h2>
            <span className="dashboard-asof-badge px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-winsor-950 text-winsor-300 border border-winsor-800/60 font-mono flex items-center">
              MARKET SNAPSHOT
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
              Your market overview and investment intelligence · prices as of{' '}
            <span className="text-winsor-400 font-mono font-bold">
              {data.market_data_asof || 'unavailable'}
            </span>
              {data.latest_asof && <span> · strategy weights as of <span className="text-winsor-400 font-mono font-bold">{data.latest_asof}</span></span>}
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

      <MarketBenchmarkPanel liveQuote={macro?.is_live ? macro.nifty_50 : null} liveAsOf={data.market_data_asof} />

      {/* Point-in-time market breadth and leadership from stored price history. */}
      <section className="dashboard-market-pulse space-y-3" aria-label="Market session statistics">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div><span className="market-section-kicker">MARKET PULSE</span><h3 className="text-lg font-bold text-white">Breadth & leadership</h3></div>
          <span className="text-[10px] font-mono text-slate-500">Daily price snapshot · {data.market_snapshot?.asof_date || data.market_data_asof || 'date unavailable'}</span>
        </div>
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
          {[
            { label: 'Market breadth', value: data.market_snapshot ? `${data.market_snapshot.advancing.toLocaleString('en-IN')} / ${data.market_snapshot.declining.toLocaleString('en-IN')}` : '—', detail: 'Advancing / declining stocks', tone: 'text-emerald-700' },
            { label: '52-week range', value: data.market_snapshot?.year_range_symbols ? `${data.market_snapshot.new_52w_highs} / ${data.market_snapshot.new_52w_lows}` : '—', detail: data.market_snapshot?.year_range_symbols ? `New highs / lows · ${data.market_snapshot.year_range_symbols} stocks with ≥245 sessions` : 'Insufficient stored history', tone: 'text-winsor-500' },
            { label: 'India VIX', value: macro?.is_live ? safeToFixed(macro.india_vix, 2) : '—', detail: macro?.is_live ? 'Live volatility index' : 'Live quote unavailable', tone: 'text-winsor-500' },
            { label: 'FII / DII flows', value: 'Unavailable', detail: 'No connected flow source; no estimate shown', tone: 'text-slate-500' },
          ].map((item) => <div key={item.label} className="market-stat-card rounded-2xl border border-white/10 bg-slate-900/35 p-4">
            <span className="text-[10px] font-bold uppercase tracking-[.12em] text-slate-500">{item.label}</span>
            <strong className={`mt-2 block font-mono text-xl ${item.tone}`}>{item.value}</strong>
            <span className="mt-1 block text-[11px] text-slate-500">{item.detail}</span>
          </div>)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div className="market-stat-card rounded-2xl border border-white/10 bg-slate-900/35 p-4">
            <div className="mb-3 flex items-center justify-between"><h4 className="text-sm font-bold text-white">Sector performance</h4><span className="text-[10px] text-slate-500">equal-weighted daily move</span></div>
            {data.market_snapshot?.sector_performance?.length ? <div className="space-y-3">{data.market_snapshot.sector_performance.map((sector) => <div key={sector.sector} className="grid grid-cols-[minmax(8rem,1fr)_minmax(5rem,1.2fr)_auto] items-center gap-3 text-xs"><span className="truncate capitalize text-slate-400">{sector.sector.replace(/_/g, ' ')}</span><span className="h-1.5 overflow-hidden rounded-full bg-stone-200"><i className={`block h-full rounded-full ${sector.change_pct >= 0 ? 'bg-emerald-600' : 'bg-rose-600'}`} style={{ width: `${Math.min(100, Math.max(4, Math.abs(sector.change_pct) * 3))}%` }} /></span><span className={`font-mono font-bold ${sector.change_pct >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{sector.change_pct > 0 ? '+' : ''}{sector.change_pct.toFixed(2)}%</span></div>)}</div> : <p className="py-4 text-xs text-slate-500">Sector coverage is unavailable for this stored-price snapshot.</p>}
          </div>
          <div className="market-stat-card rounded-2xl border border-white/10 bg-slate-900/35 p-4">
            <div className="mb-3 flex items-center justify-between"><h4 className="text-sm font-bold text-white">Top movers</h4><span className="text-[10px] text-slate-500">largest absolute daily changes</span></div>
            {data.market_snapshot?.top_movers?.length ? <div className="space-y-2.5">{data.market_snapshot.top_movers.map((mover) => <div key={mover.symbol} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 text-xs"><span className="font-mono font-bold text-slate-300">{mover.symbol}</span><span className="font-mono text-slate-500">₹{mover.close.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span><span className={`font-mono font-bold ${mover.change_pct >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{mover.change_pct > 0 ? '+' : ''}{mover.change_pct.toFixed(2)}%</span></div>)}</div> : <p className="py-4 text-xs text-slate-500">No comparable daily closes are available for movers.</p>}
          </div>
        </div>
        {!!data.market_snapshot?.excluded_extreme_moves && <p className="text-[10px] text-slate-500">{data.market_snapshot.excluded_extreme_moves} extreme move{data.market_snapshot.excluded_extreme_moves === 1 ? '' : 's'} excluded pending corporate-action verification.</p>}
      </section>

      {/* Critical Redline & Sector Alerts */}
      {mainPort?.critical_redline_alerts && mainPort.critical_redline_alerts.length > 0 && (
        <div className="dashboard-critical-alert p-4 bg-rose-950/40 border border-rose-800/60 rounded-2xl text-rose-200">
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
        <div className="dashboard-critical-alert p-4 bg-amber-950/40 border border-amber-800/60 rounded-2xl text-amber-200">
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
      <div className="dashboard-kpis grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Total Portfolio Value"
          value={hasMainHoldings ? `₹${safeToLocale(Math.round(safeNum(mainPort?.total_current_value)))}` : '₹0'}
          subtitle={hasMainHoldings ? `Total Invested: ₹${safeToLocale(Math.round(safeNum(mainPort?.total_invested)))}` : 'No active holdings'}
          delta={hasMainHoldings ? `${safeNum(mainPort?.total_unrealized_pnl_pct) >= 0 ? '+' : ''}${safeToFixed(mainPort?.total_unrealized_pnl_pct, 2)}% Return` : '0.00%'}
          deltaPositive={hasMainHoldings ? safeNum(mainPort?.total_unrealized_pnl) >= 0 : true}
          icon={Wallet}
          variant="emerald"
        />
        <KPICard
          label="Portfolio Health Score"
          value={hasMainHoldings ? `${safeToFixed(mainPort?.overall_health_score, 1)}/100` : 'N/A'}
          subtitle={hasMainHoldings ? `Grade: ${mainPort?.overall_health_grade || 'NEUTRAL'}` : 'Audit pending'}
          delta={hasMainHoldings ? `Quality: ${safeToFixed(mainPort?.weighted_business_score, 0)} | Val: ${safeToFixed(mainPort?.weighted_valuation_score, 0)}` : 'No score'}
          deltaPositive={hasMainHoldings ? safeNum(mainPort?.overall_health_score) >= 60 : true}
          icon={TrendingUp}
          variant="winsor"
        />
        <KPICard
          label="NSE Market Volatility"
          value={macro?.is_live ? safeToFixed(macro.india_vix, 2) : '—'}
          subtitle={macro?.is_live ? macro.regime_description : 'Live India VIX unavailable'}
          delta={macro?.is_live ? `${macro.regime} Regime` : 'Unavailable'}
          deltaPositive={!macro?.is_live || macro.regime !== 'HIGH_VOLATILITY'}
          icon={Activity}
          variant={macro?.regime === 'HIGH_VOLATILITY' ? 'amber' : 'info'}
        />
        <KPICard
          label="Active Positions"
          value={hasMainHoldings ? `${mainPort?.holdings_count || positions.length} Stocks` : modelHoldings.length > 0 ? `${modelHoldings.length} Target` : '—'}
          subtitle={hasMainHoldings ? (mainPort?.portfolio_name || 'Main Portfolio') : modelHoldings.length > 0 ? 'Algorithmic target model' : 'No model run available'}
          delta={hasMainHoldings ? ((mainPort?.critical_redline_alerts?.length ?? 0) === 0 ? 'Zero Redlines' : `${mainPort?.critical_redline_alerts?.length} Redline Alert`) : modelHoldings.length > 0 ? 'Model Target' : 'Unavailable'}
          deltaPositive={hasMainHoldings ? (mainPort?.critical_redline_alerts?.length ?? 0) === 0 : true}
          icon={PieChart}
          variant="purple"
        />
      </div>

      {/* 4. Real Stock Weight & Performance Attribution + Market Regime Arc Dial */}
      <div className="dashboard-allocation-analysis grid grid-cols-1 lg:grid-cols-12 gap-6">
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
          {macro?.is_live ? (
            <MarketRegimeArcGauge
              regime={macro.regime}
              vix={macro.india_vix}
              description={macro.regime_description}
            />
          ) : (
            <div className="glass-panel h-full min-h-64 p-6 flex flex-col justify-center">
              <h3 className="text-sm font-semibold text-white">Market regime unavailable</h3>
              <p className="mt-2 text-xs text-slate-400">The dashboard has no current macro pulse to display.</p>
            </div>
          )}
        </div>
      </div>

      {/* Sector exposure distribution */}
      {((mainPort?.sector_exposures && Object.keys(mainPort.sector_exposures).length > 0) ||
        (data.sector_allocations && Object.keys(data.sector_allocations).length > 0)) && (
        <div className="dashboard-sector-allocation">
          <SectorAllocation
            sectors={
              mainPort?.sector_exposures && Object.keys(mainPort.sector_exposures).length > 0
                ? mainPort.sector_exposures
                : (data.sector_allocations || {})
            }
          />
        </div>
      )}

      {/* Portfolio holdings and model table */}
      <div className="dashboard-holdings glass-panel overflow-hidden">
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
                    <th className="py-3.5 px-4">Holding</th>
                    <th className="py-3.5 px-4">Shares / cost</th>
                    <th className="py-3.5 px-4 text-right">CMP / value</th>
                    <th className="py-3.5 px-4 w-36">Weight</th>
                    <th className="py-3.5 px-4 text-right">Unrealized P&L</th>
                    <th className="py-3.5 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-medium">
                  {positions.map((p) => {
                    const pnl = safeNum(p.unrealized_pnl, 0);
                    const pnlPct = safeNum(p.unrealized_pnl_pct, 0);
                    const pnlSign = pnl >= 0 ? '+' : '';
                    const isPositive = pnl >= 0;
                    const weight = safeNum(p.weight_pct, 0);
                    const sectorName = String(p.sector || 'General').replace(/_/g, ' ');

                    const action = p.action_badge || 'HOLD';
                    const isAccumulate = action.includes('ACCUMULATE') || action.includes('BUY');
                    const isTrim = action.includes('TRIM') || action.includes('REBALANCE') || action.includes('SELL');

                    return (
                      <tr
                        key={p.symbol}
                        className="hover:bg-sky-500/[0.04] transition-all duration-150 group border-l-2 border-transparent hover:border-sky-400"
                      >
                        <td className="py-3.5 px-4">
                          <span className="block font-black text-white font-mono text-sm tracking-tight group-hover:text-sky-300 transition-colors">{p.symbol}</span>
                          <span className="mt-0.5 block text-[10px] capitalize text-slate-500">{sectorName}</span>
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-300">
                          {safeToLocale(p.shares)}
                          <span className="block text-[10px] text-slate-500">Avg ₹{safeToLocale(p.buy_price, 2)}</span>
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono font-bold text-white">
                          ₹{safeToLocale(p.current_price, 2)}
                          <span className="block text-[10px] font-normal text-slate-500">₹{safeToLocale(Math.round(safeNum(p.current_value)))}</span>
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
                        <td className="py-3.5 px-4 text-center" title={p.action_rationale || ''}>
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
