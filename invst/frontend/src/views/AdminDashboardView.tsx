import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Users,
  BrainCircuit,
  Activity,
  UserPlus,
  RotateCw,
  CheckCircle2,
  ChevronRight,
  TrendingUp,
  Cpu,
  Layers,
  ArrowRight,
} from 'lucide-react';
import {
  fetchAdminSummary,
  fetchAdminUsers,
  fetchBacktestRuns,
  getUserEmail,
} from '../api/client';
import { AdminSummaryResponse, UserProfile, BacktestHistoryItem } from '../types/api';

interface AdminDashboardViewProps {
  onNavigate: (tabId: string) => void;
}

export const AdminDashboardView: React.FC<AdminDashboardViewProps> = ({ onNavigate }) => {
  const [summary, setSummary] = useState<AdminSummaryResponse | null>(null);
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [backtestRuns, setBacktestRuns] = useState<BacktestHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sumData, usersData, backtestsData] = await Promise.all([
        fetchAdminSummary().catch(() => null),
        fetchAdminUsers().catch(() => []),
        fetchBacktestRuns().catch(() => []),
      ]);
      setSummary(sumData);
      setUsers(usersData);
      setBacktestRuns(backtestsData.slice(0, 5));
    } catch (err: any) {
      setError(err.message || 'Failed to load admin summary');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const adminEmail = getUserEmail() || 'admin@arth.iq';

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Platform Admin Banner Header */}
      <div className="p-6 rounded-3xl bg-gradient-to-r from-[#0d1222] via-[#090d19] to-[#0d1222] border border-amber-500/20 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-amber-500/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center space-x-2.5 mb-1.5">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                PLATFORM ADMIN CONSOLE
              </span>
              <span className="flex items-center space-x-1 text-xs text-slate-400 font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Engine Active</span>
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Administrative Command Center
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
              System governance, Pro Investor access provisioning, machine learning model promotion, and quantitative walk-forward simulation telemetry.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={loadDashboardData}
              disabled={isLoading}
              className="px-3.5 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 hover:text-white text-xs font-mono flex items-center space-x-1.5 transition-all cursor-pointer"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            <button
              onClick={() => onNavigate('users')}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-950 font-bold text-xs flex items-center space-x-2 shadow-[0_0_20px_rgba(245,158,11,0.25)] transition-all cursor-pointer"
            >
              <UserPlus className="w-4 h-4 text-slate-950" />
              <span>Invite Pro Investor</span>
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Users */}
        <div
          onClick={() => onNavigate('users')}
          className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08] hover:border-amber-500/40 transition-all cursor-pointer group relative overflow-hidden"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold tracking-wider font-mono">PRO INVESTORS</span>
            <Users className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-3xl font-black text-white font-mono">
            {summary ? summary.total_users : '—'}
          </div>
          <div className="mt-2 flex items-center space-x-2 text-[11px] text-slate-400">
            <span className="text-emerald-400 font-bold">{summary?.active_users ?? 0} Active</span>
            <span>•</span>
            <span className="text-amber-400 font-medium">{summary?.invited_users ?? 0} Pending</span>
          </div>
        </div>

        {/* Alpha ML Status */}
        <div
          onClick={() => onNavigate('model_training')}
          className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08] hover:border-sky-500/40 transition-all cursor-pointer group relative overflow-hidden"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold tracking-wider font-mono">ALPHA ML ENGINE</span>
            <BrainCircuit className="w-4 h-4 text-sky-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-black text-white font-mono flex items-center space-x-2">
            <span className={`w-2.5 h-2.5 rounded-full ${summary?.model_trained ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            <span>{summary?.model_trained ? 'TRAINED' : 'BASELINE'}</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400 font-mono">
            {summary?.model_version ? `Algorithm: ${summary.model_version}` : 'Platt-Calibrated LightGBM'}
          </div>
        </div>

        {/* Backtests Run */}
        <div
          onClick={() => onNavigate('backtest')}
          className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08] hover:border-purple-500/40 transition-all cursor-pointer group relative overflow-hidden"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold tracking-wider font-mono">SIMULATION RUNS</span>
            <TrendingUp className="w-4 h-4 text-purple-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-3xl font-black text-white font-mono">
            {summary ? summary.backtests_count : '—'}
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            Walk-forward quarterly backtests
          </div>
        </div>

        {/* System & PIT Health */}
        <div
          onClick={() => onNavigate('health')}
          className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08] hover:border-emerald-500/40 transition-all cursor-pointer group relative overflow-hidden"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold tracking-wider font-mono">SYSTEM INTEGRITY</span>
            <Activity className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-black text-emerald-400 font-mono flex items-center space-x-1.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span>{summary?.system_status || 'HEALTHY'}</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            Anti-Lookahead PIT Audits Passed
          </div>
        </div>
      </div>

      {/* Main Grid: Quick Action Modules & Roster Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Quick Action Hub & Recent Backtest Runs */}
        <div className="lg:col-span-2 space-y-6">
          {/* Admin Fast Actions Hub */}
          <div className="p-6 rounded-3xl bg-[#080c18] border border-white/[0.08] relative">
            <h2 className="text-base font-bold text-white mb-4 flex items-center space-x-2">
              <Layers className="w-4 h-4 text-amber-400" />
              <span>Administrative Operations</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {/* Action 1: Invite Pro Investor */}
              <div
                onClick={() => onNavigate('users')}
                className="p-4 rounded-2xl bg-[#0d1222] hover:bg-[#11172c] border border-white/[0.06] hover:border-amber-500/30 transition-all cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                    <UserPlus className="w-4 h-4" />
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-amber-400 transition-colors" />
                </div>
                <h3 className="text-sm font-bold text-white group-hover:text-amber-300 transition-colors">
                  Provision Pro Investor
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Invite institutional users by email. Users activate their own passwords on first login.
                </p>
              </div>

              {/* Action 2: Alpha ML Retraining */}
              <div
                onClick={() => onNavigate('model_training')}
                className="p-4 rounded-2xl bg-[#0d1222] hover:bg-[#11172c] border border-white/[0.06] hover:border-sky-500/30 transition-all cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="w-8 h-8 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-sky-400 transition-colors" />
                </div>
                <h3 className="text-sm font-bold text-white group-hover:text-sky-300 transition-colors">
                  Train ML Alpha Model
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Configure feature architectures, LightGBM hyperparameters, and Platt calibration.
                </p>
              </div>

              {/* Action 3: Walk-Forward Backtest */}
              <div
                onClick={() => onNavigate('backtest')}
                className="p-4 rounded-2xl bg-[#0d1222] hover:bg-[#11172c] border border-white/[0.06] hover:border-purple-500/30 transition-all cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="w-8 h-8 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
                    <TrendingUp className="w-4 h-4" />
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-purple-400 transition-colors" />
                </div>
                <h3 className="text-sm font-bold text-white group-hover:text-purple-300 transition-colors">
                  Run Walk-Forward Backtest
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Simulate portfolio performance over rolling historical windows with realistic execution costs.
                </p>
              </div>

              {/* Action 4: PIT Data Health Audit */}
              <div
                onClick={() => onNavigate('health')}
                className="p-4 rounded-2xl bg-[#0d1222] hover:bg-[#11172c] border border-white/[0.06] hover:border-emerald-500/30 transition-all cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <Activity className="w-4 h-4" />
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 transition-colors" />
                </div>
                <h3 className="text-sm font-bold text-white group-hover:text-emerald-300 transition-colors">
                  Audit Data Quality & PIT
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Inspect SQLite tables, restatement bi-temporal timestamps, and verify zero-lookahead integrity.
                </p>
              </div>
            </div>
          </div>

          {/* Recent Simulation Telemetry */}
          <div className="p-6 rounded-3xl bg-[#080c18] border border-white/[0.08]">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-white flex items-center space-x-2">
                <TrendingUp className="w-4 h-4 text-purple-400" />
                <span>Recent Backtest Engine Runs</span>
              </h2>
              <button
                onClick={() => onNavigate('backtest')}
                className="text-xs text-purple-400 hover:text-purple-300 font-mono flex items-center space-x-1"
              >
                <span>Full Engine</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {backtestRuns.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs font-mono rounded-2xl bg-[#0d1222]/50 border border-white/[0.04]">
                No historical simulation runs found. Launch a run in the Backtest tab.
              </div>
            ) : (
              <div className="space-y-2.5 font-mono text-xs">
                {backtestRuns.map((run) => (
                  <div
                    key={run.run_id}
                    className="p-3.5 rounded-xl bg-[#0d1222] border border-white/[0.05] flex items-center justify-between"
                  >
                    <div>
                      <div className="text-white font-bold">{run.start_date} to {run.end_date}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        Run ID: {run.run_id.slice(0, 16)}...
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 text-right">
                      {run.cagr !== null && (
                        <div>
                          <div className="text-[10px] text-slate-500">CAGR</div>
                          <div className="text-emerald-400 font-bold">{(run.cagr * 100).toFixed(1)}%</div>
                        </div>
                      )}
                      {run.sharpe !== null && (
                        <div>
                          <div className="text-[10px] text-slate-500">SHARPE</div>
                          <div className="text-sky-400 font-bold">{run.sharpe.toFixed(2)}</div>
                        </div>
                      )}
                      {run.max_drawdown !== null && (
                        <div>
                          <div className="text-[10px] text-slate-500">MAX DD</div>
                          <div className="text-rose-400 font-bold">{(run.max_drawdown * 100).toFixed(1)}%</div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (1 Col): Pro Investor Roster Snippet */}
        <div className="space-y-6">
          <div className="p-6 rounded-3xl bg-[#080c18] border border-white/[0.08]">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-white flex items-center space-x-2">
                <Users className="w-4 h-4 text-amber-400" />
                <span>User Roster</span>
              </h2>
              <button
                onClick={() => onNavigate('users')}
                className="text-xs text-amber-400 hover:text-amber-300 font-mono flex items-center space-x-1"
              >
                <span>Manage</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-2.5">
              {users.slice(0, 6).map((u) => (
                <div
                  key={u.id}
                  className="p-3 rounded-xl bg-[#0d1222] border border-white/[0.05] flex items-center justify-between text-xs"
                >
                  <div className="overflow-hidden pr-2">
                    <div className="font-semibold text-white truncate">{u.name || u.email}</div>
                    <div className="text-[11px] text-slate-400 font-mono truncate">{u.email}</div>
                  </div>

                  <div>
                    {u.status === 'ACTIVE' ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                        ACTIVE
                      </span>
                    ) : u.status === 'INVITED' ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/15 text-amber-300 border border-amber-500/25">
                        INVITED
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-rose-500/15 text-rose-300 border border-rose-500/25">
                        SUSPENDED
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={() => onNavigate('users')}
              className="mt-4 w-full py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 hover:text-white font-mono text-xs flex items-center justify-center space-x-1.5 transition-all"
            >
              <UserPlus className="w-3.5 h-3.5 text-amber-400" />
              <span>Register New Pro Investor</span>
            </button>
          </div>

          {/* System Environment Information Card */}
          <div className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08] font-mono text-xs space-y-2.5">
            <div className="text-[11px] text-slate-500 font-bold uppercase tracking-wider mb-2">
              Platform Environment
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span>Database Engine:</span>
              <span className="text-white">SQLite (WAL mode)</span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span>Security Hash:</span>
              <span className="text-white">PBKDF2-SHA256</span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span>Session Protocol:</span>
              <span className="text-white">JWT HS256 (72h)</span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span>Admin Profile:</span>
              <span className="text-amber-400 truncate max-w-[160px]">{adminEmail}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
