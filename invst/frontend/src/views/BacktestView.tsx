import React, { useEffect, useState } from 'react';
import { runBacktest, fetchBacktestRuns } from '../api/client';
import { BacktestRunResponse, BacktestHistoryItem } from '../types/api';
import { KPICard } from '../components/KPICard';
import { EquityChart } from '../components/EquityChart';
import {
  Play,
  LineChart,
  History,
  TrendingUp,
  ShieldAlert,
  Award,
  Activity,
  RefreshCw,
  Flame,
} from 'lucide-react';

export const BacktestView: React.FC = () => {
  const [startDate, setStartDate] = useState<string>('2022-01-01');
  const [endDate, setEndDate] = useState<string>('2024-03-31');
  const [initialCapital, setInitialCapital] = useState<number>(1000000);
  const [targetHoldings, setTargetHoldings] = useState<number>(8);
  const [benchmarkSymbol, setBenchmarkSymbol] = useState<string>('NIFTY500');

  const [running, setRunning] = useState<boolean>(false);
  const [currentResult, setCurrentResult] = useState<BacktestRunResponse | null>(null);
  const [history, setHistory] = useState<BacktestHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = async () => {
    try {
      const runs = await fetchBacktestRuns();
      setHistory(runs);
    } catch (err) {
      console.error('Failed to load past backtest runs', err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleRunBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setError(null);
    try {
      const res = await runBacktest({
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        target_holdings: targetHoldings,
        benchmark_symbol: benchmarkSymbol,
      });
      setCurrentResult(res);
      await loadHistory();
    } catch (err: any) {
      setError(err.message || 'Backtest execution failed');
    } finally {
      setRunning(false);
    }
  };

  const applyRegime = (start: string, end: string, bench: string = 'NIFTY500') => {
    setStartDate(start);
    setEndDate(end);
    setBenchmarkSymbol(bench);
  };

  const formatPct = (val?: number | null) => (val !== undefined && val !== null ? `${(val * 100).toFixed(2)}%` : '—');
  const formatNum = (val?: number | null) => (val !== undefined && val !== null ? val.toFixed(2) : '—');

  const m = currentResult?.metrics;

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-winsor-700 via-winsor-600 to-sky-400 p-0.5 shadow-[0_0_20px_rgba(37,99,235,0.35)] flex items-center justify-center">
              <div className="w-full h-full bg-[#080a12] rounded-[14px] flex items-center justify-center">
                <LineChart className="w-5 h-5 text-sky-400" />
              </div>
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                Walk-Forward Simulation Engine
              </h1>
              <p className="text-xs text-slate-400 mt-0.5 font-sans">
                Quarterly walk-forward validation enforcing point-in-time constraints, 15 bps slippage, and STT
              </p>
            </div>
          </div>
        </div>

        {/* Quick Regime Presets */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-500 font-bold flex items-center font-mono">
            <Flame className="w-3.5 h-3.5 mr-1 text-amber-400" /> Presets:
          </span>
          <button
            onClick={() => applyRegime('2020-01-01', '2021-06-30')}
            className="px-2.5 py-1 rounded-xl bg-[#06080e] border border-white/[0.08] text-slate-300 hover:text-white hover:border-winsor-500/40 transition-all font-mono"
          >
            COVID Recovery (2020-21)
          </button>
          <button
            onClick={() => applyRegime('2022-01-01', '2023-12-31')}
            className="px-2.5 py-1 rounded-xl bg-[#06080e] border border-white/[0.08] text-slate-300 hover:text-white hover:border-winsor-500/40 transition-all font-mono"
          >
            Rate Hike Regime (2022-23)
          </button>
          <button
            onClick={() => applyRegime('2022-01-01', '2024-03-31')}
            className="px-2.5 py-1 rounded-xl bg-[#06080e] border border-white/[0.08] text-slate-300 hover:text-white hover:border-winsor-500/40 transition-all font-mono"
          >
            Full Period (2022-24)
          </button>
        </div>
      </div>

      {/* Configuration Form */}
      <form
        onSubmit={handleRunBacktest}
        className="glass-card rounded-3xl p-6 border border-white/[0.08] shadow-2xl space-y-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider font-mono">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
              className="w-full bg-[#06080e] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-white font-mono outline-none focus:border-sky-400 shadow-inner"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider font-mono">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
              className="w-full bg-[#06080e] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-white font-mono outline-none focus:border-sky-400 shadow-inner"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider font-mono">
              Initial Capital (₹)
            </label>
            <input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Math.max(500, Number(e.target.value)))}
              min={500}
              step={5000}
              required
              className="w-full bg-[#06080e] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-white font-mono outline-none focus:border-sky-400 shadow-inner"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider font-mono">
              Target Holdings (1–50)
            </label>
            <input
              type="number"
              min={1}
              max={50}
              value={targetHoldings}
              onChange={(e) => setTargetHoldings(Math.max(1, Math.min(50, Number(e.target.value))))}
              required
              className="w-full bg-[#06080e] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-white font-mono outline-none focus:border-sky-400 shadow-inner"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase tracking-wider font-mono">
              Benchmark
            </label>
            <select
              value={benchmarkSymbol}
              onChange={(e) => setBenchmarkSymbol(e.target.value)}
              className="w-full bg-[#06080e] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-white font-bold outline-none focus:border-sky-400 shadow-inner"
            >
              <option value="NIFTY500" className="bg-[#0b0e17]">NIFTY 500 TRI</option>
              <option value="NIFTY50" className="bg-[#0b0e17]">NIFTY 50</option>
            </select>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between pt-3 border-t border-white/[0.06] gap-3">
          <span className="text-xs text-slate-400 font-mono">
            Quarterly Cadence • Buy friction: <span className="text-emerald-400 font-bold">0.15%</span> • Sell friction: <span className="text-rose-400 font-bold">0.15%</span>
          </span>
          <button
            type="submit"
            disabled={running}
            className={`flex items-center space-x-2 px-5 py-2.5 rounded-xl text-xs font-black shadow-lg transition-all ${
              running
                ? 'bg-[#0a0d17] text-slate-400 cursor-not-allowed border border-white/[0.08]'
                : 'bg-gradient-to-r from-winsor-700 via-winsor-600 to-sky-500 hover:brightness-110 text-white shadow-[0_0_18px_rgba(37,99,235,0.4)]'
            }`}
          >
            {running ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-sky-400" />
                <span>Simulating Walk-Forward Regimes...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Execute Walk-Forward Simulation</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-rose-950/20 border border-rose-800 rounded-xl text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Results Section */}
      {currentResult && m && (
        <div className="space-y-6">
          {/* Equity Chart with Underwater Drawdowns & Timeframes */}
          <EquityChart
            dates={currentResult.equity_dates}
            portfolioValues={currentResult.portfolio_equity}
            benchmarkValues={currentResult.benchmark_equity}
            benchmarkLabel={benchmarkSymbol}
          />

          {/* Performance KPIs with Sparklines */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <KPICard
              label="Strategy CAGR"
              value={formatPct(m.cagr)}
              subtitle={`Benchmark: ${formatPct(m.benchmark_cagr)}`}
              icon={TrendingUp}
              variant={m.cagr && m.benchmark_cagr && m.cagr > m.benchmark_cagr ? 'success' : 'default'}
              sparkline={true}
              trendPositive={m.cagr !== null && m.cagr > 0}
            />
            <KPICard
              label="Sharpe Ratio"
              value={formatNum(m.sharpe)}
              subtitle={`Benchmark: ${formatNum(m.benchmark_sharpe)}`}
              icon={Award}
              variant="purple"
              sparkline={false}
            />
            <KPICard
              label="Max Drawdown"
              value={formatPct(m.max_drawdown)}
              subtitle={`Benchmark: ${formatPct(m.benchmark_max_drawdown)}`}
              icon={ShieldAlert}
              variant={m.max_drawdown && m.max_drawdown > -0.2 ? 'success' : 'warning'}
              sparkline={true}
              trendPositive={m.max_drawdown !== null && m.max_drawdown > -0.2}
            />
            <KPICard
              label="Sortino Ratio"
              value={formatNum(m.sortino)}
              subtitle={`Calmar: ${formatNum(m.calmar)}`}
              icon={Activity}
              variant="info"
              sparkline={false}
            />
          </div>

          {/* Additional Institutional Quant Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 glass-card rounded-2xl border border-slate-800 text-xs font-mono">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400 block font-sans text-[11px]">Annualized Volatility</span>
              <span className="font-bold text-slate-200 text-sm">{formatPct(m.annualized_vol)}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400 block font-sans text-[11px]">Average Rebalance Turnover</span>
              <span className="font-bold text-slate-200 text-sm">{formatPct(m.turnover_avg)}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400 block font-sans text-[11px]">Quarterly Outperformance Hit Rate</span>
              <span className="font-bold text-emerald-400 text-sm">{formatPct(m.hit_rate)}</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="text-slate-400 block font-sans text-[11px]">Simulated Rebalance Periods</span>
              <span className="font-bold text-cyan-400 text-sm">{m.rebalance_count} quarters</span>
            </div>
          </div>
        </div>
      )}

      {/* Historical Runs Table */}
      <div className="glass-card rounded-2xl overflow-hidden shadow-2xl border border-slate-800">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
          <div className="flex items-center space-x-2">
            <History className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-black uppercase tracking-wider text-white">
              Historical Backtest Execution Log
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-mono font-bold">{history.length} saved runs</span>
        </div>

        {history.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No previous backtest runs recorded. Trigger a run above to save results.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/90 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Run ID</th>
                  <th className="py-3 px-4">Simulation Window</th>
                  <th className="py-3 px-4 text-right">Strategy CAGR</th>
                  <th className="py-3 px-4 text-right">Benchmark CAGR</th>
                  <th className="py-3 px-4 text-right">Sharpe</th>
                  <th className="py-3 px-4 text-right">Max DD</th>
                  <th className="py-3 px-4 text-right">Turnover</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {history.map((run) => (
                  <tr key={run.run_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-bold text-slate-200">
                      {run.run_id.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-sans">
                      {run.start_date} → {run.end_date}
                    </td>
                    <td className="py-3 px-4 text-right font-black text-emerald-400">
                      {formatPct(run.cagr)}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-400">
                      {formatPct(run.benchmark_cagr)}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-purple-300">
                      {formatNum(run.sharpe)}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-rose-400">
                      {formatPct(run.max_drawdown)}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-300">
                      {formatPct(run.turnover_avg)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {run.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
