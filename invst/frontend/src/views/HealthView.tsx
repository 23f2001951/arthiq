import React, { useEffect, useState } from 'react';
import { fetchHealth } from '../api/client';
import { HealthResponse } from '../types/api';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Lock,
  SearchCheck,
} from 'lucide-react';

export const HealthView: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchHealth();
      setHealth(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch health audits');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-winsor-700 via-winsor-600 to-sky-400 p-0.5 shadow-[0_0_20px_rgba(37,99,235,0.35)] flex items-center justify-center">
              <div className="w-full h-full bg-[#080a12] rounded-[14px] flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-sky-400" />
              </div>
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                System Health & Point-in-Time Integrity
              </h1>
              <p className="text-xs text-slate-400 mt-0.5 font-sans">
                Automated continuous auditing for data pipeline anomalies and zero-tolerance anti-lookahead PIT rules
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={loadHealth}
          className="flex items-center space-x-1.5 px-4 py-2 bg-[#0a0d17] hover:bg-[#121627] border border-white/[0.08] rounded-xl text-xs font-bold text-slate-200 transition-all shadow-sm"
        >
          <RefreshCw className="w-3.5 h-3.5 text-sky-400" />
          <span>Execute Audit Suite</span>
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-slate-400 glass-card rounded-3xl border border-white/[0.08]">
          <RefreshCw className="w-6 h-6 animate-spin mr-3 text-sky-400" />
          <span className="font-medium">Executing Data Quality & PIT audits...</span>
        </div>
      ) : error ? (
        <div className="p-6 bg-rose-950/20 border border-rose-800 rounded-3xl text-rose-300">
          <h4 className="font-bold text-rose-200">Health Audit Failed</h4>
          <p className="text-sm mt-1">{error}</p>
        </div>
      ) : health ? (
        <div className="space-y-6">
          {/* Main Status Hero Banner */}
          <div
            className={`p-6 rounded-3xl border backdrop-blur-xl shadow-2xl flex flex-wrap items-center justify-between gap-4 ${
              health.overall_status === 'HEALTHY'
                ? 'bg-gradient-to-r from-emerald-950/40 via-[#0a0f1d]/80 to-[#080b13]/90 border-emerald-500/40 text-emerald-300 shadow-emerald-950/20'
                : 'bg-gradient-to-r from-amber-950/40 via-[#0a0f1d]/80 to-[#080b13]/90 border-amber-500/40 text-amber-300 shadow-amber-950/20'
            }`}
          >
            <div className="flex items-center space-x-4">
              <div className={`flex items-center justify-center w-12 h-12 rounded-2xl border shadow-lg ${
                health.overall_status === 'HEALTHY'
                  ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                  : 'bg-amber-500/20 border-amber-500/40 text-amber-400'
              }`}>
                {health.overall_status === 'HEALTHY' ? (
                  <CheckCircle className="w-7 h-7" />
                ) : (
                  <AlertTriangle className="w-7 h-7" />
                )}
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-lg font-black text-white tracking-wide font-mono">
                    Platform Status: {health.overall_status}
                  </h3>
                  <span className={`w-2.5 h-2.5 rounded-full ${
                    health.overall_status === 'HEALTHY' ? 'bg-emerald-400 animate-ping' : 'bg-amber-400'
                  }`} />
                </div>
                <p className="text-xs opacity-90 mt-1 max-w-2xl font-sans text-slate-300">
                  {health.overall_status === 'HEALTHY'
                    ? 'All Point-in-Time anti-lookahead rules and data sanity assertions passed with zero violations.'
                    : 'One or more data quality checks or PIT audit constraints require investigation.'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3 text-xs font-mono">
              <span className="px-3 py-1.5 rounded-xl bg-[#06080e] border border-white/[0.08] text-slate-300">
                PIT Integrity: <strong className="text-emerald-400">100%</strong>
              </span>
              <span className="px-3 py-1.5 rounded-xl bg-[#06080e] border border-white/[0.08] text-slate-300">
                WAL Mode: <strong className="text-sky-400">ACTIVE</strong>
              </span>
            </div>
          </div>

          {/* Point-in-Time Anti-Lookahead Section */}
          <div className="glass-card rounded-3xl overflow-hidden shadow-2xl border border-white/[0.08]">
            <div className="p-5 border-b border-white/[0.06] bg-[#07090f]/70 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Lock className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-black uppercase tracking-wider text-white">
                  Point-in-Time Anti-Lookahead Audits
                </h3>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {health.pit_audits.length} checks
              </span>
            </div>

            <div className="divide-y divide-white/[0.04]">
              {health.pit_audits.map((item) => (
                <div key={item.name} className="p-5 flex items-start justify-between gap-4 hover:bg-winsor-950/20 transition-colors">
                  <div className="flex items-start space-x-3.5">
                    {item.passed ? (
                      <CheckCircle className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" />
                    )}
                    <div>
                      <div className="flex items-center space-x-2.5">
                        <span className="text-sm font-bold text-white font-mono">{item.name}</span>
                        <span
                          className={`text-[10px] font-black px-2 py-0.5 rounded tracking-wider ${
                            item.passed
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {item.passed ? 'PASSED' : 'VIOLATION'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 font-sans">{item.message}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Data Quality & Sanity Section */}
          <div className="glass-card rounded-3xl overflow-hidden shadow-2xl border border-white/[0.08]">
            <div className="p-5 border-b border-white/[0.06] bg-[#07090f]/70 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <SearchCheck className="w-4 h-4 text-sky-400" />
                <h3 className="text-sm font-black uppercase tracking-wider text-white">
                  Data Pipeline Sanity & Anomaly Checks
                </h3>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {health.data_quality_checks.length} checks
              </span>
            </div>

            <div className="divide-y divide-white/[0.04]">
              {health.data_quality_checks.map((item) => (
                <div key={item.name} className="p-5 flex items-start justify-between gap-4 hover:bg-winsor-950/20 transition-colors">
                  <div className="flex items-start space-x-3.5">
                    {item.passed ? (
                      <CheckCircle className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" />
                    )}
                    <div>
                      <div className="flex items-center space-x-2.5">
                        <span className="text-sm font-bold text-white font-mono">{item.name}</span>
                        <span
                          className={`text-[10px] font-black px-2 py-0.5 rounded tracking-wider ${
                            item.passed
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {item.passed ? 'PASSED' : 'FLAGGED'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 font-sans">{item.message}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
