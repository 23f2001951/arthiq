// IIM — Signal Card component
// Displays one active/historical intraday signal with SL/T1/T2,
// confidence meter, rationale, position sizing, and outcome buttons.

import { useState } from 'react';
import type { IntradaySignal } from '../types/intraday';

interface IntradaySignalCardProps {
  signal: IntradaySignal;
  accountCapital?: number;
  onFeedback?: (signalId: number, eventType: string, price?: number) => void;
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'text-amber-400 border-amber-400/30 bg-amber-400/5',
  ENTRY_FILLED: 'text-blue-400 border-blue-400/30 bg-blue-400/5',
  T1_HIT: 'text-emerald-400 border-emerald-400/30 bg-emerald-400/5',
  T2_HIT: 'text-emerald-300 border-emerald-300/30 bg-emerald-300/5',
  SL_HIT: 'text-red-400 border-red-400/30 bg-red-400/5',
  EXPIRED: 'text-slate-400 border-slate-700 bg-slate-800/50',
  MANUAL_EXIT: 'text-slate-300 border-slate-600 bg-slate-800/50',
  TRAILING_STOP_HIT: 'text-orange-400 border-orange-400/30 bg-orange-400/5',
};

const STATUS_LABELS: Record<string, string> = {
  PENDING: 'PENDING ENTRY',
  ENTRY_FILLED: 'ACTIVE',
  T1_HIT: 'T1 REACHED ✓',
  T2_HIT: 'T2 REACHED ✓✓',
  SL_HIT: 'STOPPED OUT',
  EXPIRED: 'EXPIRED (EOD)',
  MANUAL_EXIT: 'MANUAL EXIT',
  TRAILING_STOP_HIT: 'TRAIL STOPPED',
};

function fmt(n: number | null | undefined, dec = 2) {
  if (n == null) return '—';
  return n.toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function positionSize(sl_distance: number, capital: number, riskPct = 0.005) {
  if (sl_distance <= 0 || capital <= 0) return { shares: 0, risk: 0 };
  const risk = capital * riskPct;
  return { shares: Math.floor(risk / sl_distance), risk: Math.round(risk) };
}

export default function IntradaySignalCard({
  signal,
  accountCapital = 500000,
  onFeedback,
}: IntradaySignalCardProps) {
  const [feedbackSent, setFeedbackSent] = useState(false);
  const isActive = ['PENDING', 'ENTRY_FILLED'].includes(signal.current_status);
  const isLong = signal.signal_type === 'LONG';
  const statusClass = STATUS_COLORS[signal.current_status] ?? STATUS_COLORS.PENDING;
  const { shares, risk } = positionSize(signal.sl_distance, accountCapital);

  let pillars: string[] = [];
  try { pillars = JSON.parse(signal.pillars_met); } catch { /* */ }

  const handleFeedback = async (eventType: string) => {
    if (!onFeedback) return;
    onFeedback(signal.id, eventType);
    setFeedbackSent(true);
  };

  return (
    <div className={`rounded-xl border p-4 space-y-3 transition-all ${statusClass}`}>
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-lg font-bold ${isLong ? 'text-emerald-400' : 'text-red-400'}`}>
            {isLong ? '▲' : '▼'}
          </span>
          <span className="font-mono font-bold text-white text-base">{signal.symbol}</span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded ${isLong ? 'bg-emerald-400/10 text-emerald-400' : 'bg-red-400/10 text-red-400'}`}>
            {signal.signal_type}
          </span>
          {signal.mode === 'paper' && (
            <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300 border border-slate-600">
              ⏸ STUDY
            </span>
          )}
        </div>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${statusClass}`}>
          {STATUS_LABELS[signal.current_status] ?? signal.current_status}
        </span>
      </div>

      {/* Price grid */}
      <div className="grid grid-cols-4 gap-2 text-center">
        <div className="rounded-lg bg-slate-900/60 p-2">
          <div className="text-xs text-slate-500 mb-0.5">Entry</div>
          <div className="font-mono text-sm text-white">₹{fmt(signal.entry_price)}</div>
        </div>
        <div className="rounded-lg bg-red-950/40 p-2 border border-red-900/30">
          <div className="text-xs text-red-400 mb-0.5">SL</div>
          <div className="font-mono text-sm text-red-300">₹{fmt(signal.sl_price)}</div>
        </div>
        <div className="rounded-lg bg-emerald-950/40 p-2 border border-emerald-900/30">
          <div className="text-xs text-emerald-400 mb-0.5">T1</div>
          <div className="font-mono text-sm text-emerald-300">₹{fmt(signal.target_1)}</div>
        </div>
        <div className="rounded-lg bg-teal-950/40 p-2 border border-teal-900/30">
          <div className="text-xs text-teal-400 mb-0.5">T2</div>
          <div className="font-mono text-sm text-teal-300">₹{fmt(signal.target_2)}</div>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex flex-wrap gap-3 text-xs text-slate-400">
        <span>R:R <span className="text-white font-mono">1:{fmt(signal.reward_risk, 1)}</span></span>
        <span>ATR <span className="text-white font-mono">₹{fmt(signal.atr_at_signal)}</span></span>
        <span>VWAP <span className="text-white font-mono">₹{fmt(signal.vwap_at_signal)}</span></span>
        <span>TODVOL <span className="text-white font-mono">{fmt(signal.todvol_ratio, 1)}×</span></span>
        <span>Regime <span className="text-white font-mono">{signal.regime}</span></span>
      </div>

      {/* Confidence bar */}
      {signal.confidence_score != null && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">Signal Confidence</span>
            <span className="text-white font-mono">{signal.confidence_score}%</span>
          </div>
          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${signal.confidence_score >= 75 ? 'bg-emerald-500' : signal.confidence_score >= 55 ? 'bg-amber-500' : 'bg-red-500'}`}
              style={{ width: `${signal.confidence_score}%` }}
            />
          </div>
        </div>
      )}

      {/* Pillars */}
      {pillars.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {pillars.map(p => (
            <span key={p} className="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              ✓ {p.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}

      {/* Position sizing */}
      {isActive && shares > 0 && (
        <div className="rounded-lg bg-slate-900/80 border border-slate-700/50 p-2 text-xs flex gap-4">
          <span className="text-slate-400">Suggested size:</span>
          <span className="text-white font-mono font-bold">{shares} shares</span>
          <span className="text-slate-400">Capital at risk:</span>
          <span className="text-amber-300 font-mono">₹{risk.toLocaleString('en-IN')}</span>
        </div>
      )}

      {/* Rationale */}
      {signal.rationale && (
        <p className="text-xs text-slate-400 leading-relaxed border-l-2 border-slate-700 pl-2">
          {signal.rationale}
        </p>
      )}

      {/* P&L if closed */}
      {signal.net_pnl_r != null && (
        <div className={`text-sm font-mono font-bold ${signal.net_pnl_r >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          Net P&L: {signal.net_pnl_r >= 0 ? '+' : ''}{fmt(signal.net_pnl_r, 3)}R
          {signal.mfe_r != null && <span className="text-xs text-slate-500 ml-2">MFE: {fmt(signal.mfe_r, 2)}R</span>}
          {signal.mae_r != null && <span className="text-xs text-slate-500 ml-2">MAE: {fmt(signal.mae_r, 2)}R</span>}
        </div>
      )}

      {/* Feedback buttons (active signals only) */}
      {isActive && !feedbackSent && onFeedback && (
        <div className="flex gap-2 pt-1">
          <span className="text-xs text-slate-500 self-center">Mark outcome:</span>
          {['T1_HIT', 'T2_HIT', 'SL_HIT', 'MANUAL_EXIT'].map(evt => (
            <button
              key={evt}
              onClick={() => handleFeedback(evt)}
              className={`text-xs px-2 py-1 rounded border transition-colors ${
                evt === 'SL_HIT' ? 'border-red-800 text-red-400 hover:bg-red-950' :
                evt.includes('HIT') ? 'border-emerald-800 text-emerald-400 hover:bg-emerald-950' :
                'border-slate-700 text-slate-400 hover:bg-slate-800'
              }`}
            >
              {evt.replace('_HIT', ' ✓').replace('_', ' ')}
            </button>
          ))}
        </div>
      )}
      {feedbackSent && (
        <p className="text-xs text-emerald-400">✓ Outcome recorded. Thank you.</p>
      )}

      {/* Disclaimer */}
      {signal.mode === 'paper' && (
        <p className="text-xs text-slate-600 italic">
          ⏸ Delayed data (yfinance ~15 min). For study only — not a live entry signal.
        </p>
      )}
    </div>
  );
}
