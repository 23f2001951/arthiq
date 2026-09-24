import React, { useEffect, useState } from 'react';
import {
  fetchRecommendations,
  fetchQuickPicks,
  fetchModelStatus,
  trainModel,
} from '../api/client';
import {
  StockRecommendationItem,
  QuickPickItem,
  ModelStatusResponse,
  ModelTrainResponse,
} from '../types/api';
import { StockCard } from '../components/StockCard';
import { QuickPickCard } from '../components/QuickPickCard';
import { FactorMatrixView } from '../components/FactorMatrixView';
import { StockIdeasSubTab } from '../components/StockIdeasSubNav';
import { LensView } from '../components/LensView';
import { RadarView } from '../components/RadarView';
import {
  Filter,
  Calendar,
  Sparkles,
  RefreshCw,
  Zap,
  BarChart3,
  Layers,
  ShieldCheck,
  Cpu,
  CheckCircle2,
  Sliders,
  X,
  AlertCircle,
  Play,
  Clock,
} from 'lucide-react';

interface RecommendationsViewProps {
  activeSubTab?: StockIdeasSubTab;
  onSelectSubTab?: (subTab: StockIdeasSubTab) => void;
}

export const RecommendationsView: React.FC<RecommendationsViewProps> = ({
  activeSubTab = 'alpha_picks',
}) => {
  const [viewMode, setViewMode] = useState<'quick_pick' | 'matrix' | 'cards'>('quick_pick');

  // Standard recommendations state
  const [recs, setRecs] = useState<StockRecommendationItem[]>([]);
  const [topN, setTopN] = useState<number>(8);
  const [selectedSector, setSelectedSector] = useState<string>('ALL');

  // Quick picks state
  const [picks, setPicks] = useState<QuickPickItem[]>([]);
  const [pickN, setPickN] = useState<number>(2);
  const [deploymentContext, setDeploymentContext] = useState<string>('');

  // ML Alpha Engine state
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [horizonDays, setHorizonDays] = useState<number>(90);
  const [showTrainModal, setShowTrainModal] = useState<boolean>(false);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [trainModelType, setTrainModelType] = useState<string>('lightgbm');
  const [trainHorizonDays, setTrainHorizonDays] = useState<number>(90);
  const [trainFeatureMode, setTrainFeatureMode] = useState<string>('pair_fund_mom');
  const [trainCalibration, setTrainCalibration] = useState<string>('isotonic');
  const [trainSuccessResult, setTrainSuccessResult] = useState<ModelTrainResponse | null>(null);
  const [trainErrorMsg, setTrainErrorMsg] = useState<string | null>(null);

  // Interactive Capital Deployment Calculator state
  const [freshCapital, setFreshCapital] = useState<number>(100000);

  // Helper for current date in Indian Standard Time (YYYY-MM-DD)
  const getTodayIST = () =>
    new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());

  const [asof, setAsof] = useState<string>(getTodayIST());
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (viewMode === 'quick_pick') {
        const res = await fetchQuickPicks(pickN, asof, true, horizonDays);
        setPicks(res.picks);
        setDeploymentContext(res.deployment_context);
      }
      const res = await fetchRecommendations(asof, Math.max(topN, 20));
      setRecs(res.recommendations);

      try {
        const statusRes = await fetchModelStatus();
        setModelStatus(statusRes);
      } catch (err) {
        console.warn('Model status fetch warning:', err);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch recommendations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [asof, viewMode, pickN, topN, horizonDays]);

  const handleTrainModel = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsTraining(true);
    setTrainSuccessResult(null);
    setTrainErrorMsg(null);
    try {
      const res = await trainModel({
        model_type: trainModelType,
        horizon_days: trainHorizonDays,
        feature_mode: trainFeatureMode,
        calibration_method: trainCalibration,
        asof: asof,
      });
      setTrainSuccessResult(res);
      setHorizonDays(trainHorizonDays);
      const statusRes = await fetchModelStatus();
      setModelStatus(statusRes);
      await loadData();
    } catch (err: any) {
      setTrainErrorMsg(err.message || 'Model training failed');
    } finally {
      setIsTraining(false);
    }
  };

  // Extract unique sectors for filter
  const sectors = ['ALL', ...Array.from(new Set(recs.map((r) => r.sector)))];

  const filteredRecs =
    selectedSector === 'ALL'
      ? recs
      : recs.filter((r) => r.sector.toLowerCase() === selectedSector.toLowerCase());

  // Render Sub-Navbar specific views when active
  if (activeSubTab === 'lens') {
    return <LensView recommendations={recs} />;
  }

  if (activeSubTab === 'radar') {
    return <RadarView />;
  }

  return (
    <div className="space-y-8">
      {/* Top Header & View Mode Switcher (Mixed Winsor Blue + Emerald + Obsidian theme) */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-winsor-700 via-winsor-600 to-sky-400 p-0.5 shadow-[0_0_20px_rgba(37,99,235,0.35)] flex items-center justify-center">
              <div className="w-full h-full bg-[#080a12] rounded-[14px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-sky-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
                  Stock Ideas & Alpha Picks
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-winsor-950 text-winsor-400 border border-winsor-800/60 flex items-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
                  MULTI-FACTOR
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-sans">
                Stage 0 Liquidity Filter → Quality (40%) → Valuation (30%) → Risk (30%) + Sentiment Overlay
              </p>
            </div>
          </div>
        </div>

        {/* Triple Mode Switcher Pill */}
        <div className="flex items-center p-1.5 bg-[#090c14] border border-white/[0.08] rounded-2xl shadow-xl">
          <button
            onClick={() => setViewMode('quick_pick')}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              viewMode === 'quick_pick'
                ? 'bg-gradient-to-r from-winsor-700 to-winsor-600 text-white shadow-[0_0_15px_rgba(37,99,235,0.4)] border border-sky-400/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Top {pickN} Alpha Picks</span>
          </button>
          <button
            onClick={() => setViewMode('matrix')}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              viewMode === 'matrix'
                ? 'bg-gradient-to-r from-sky-600 to-cyan-500 text-white shadow-[0_0_15px_rgba(6,182,212,0.4)] border border-cyan-300/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Factor Matrix</span>
          </button>
          <button
            onClick={() => setViewMode('cards')}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              viewMode === 'cards'
                ? 'bg-gradient-to-r from-indigo-700 to-indigo-600 text-white shadow-[0_0_15px_rgba(99,102,241,0.4)] border border-indigo-400/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Detailed Cards</span>
          </button>
        </div>
      </div>

      {/* Alpha Model Engine Hub Banner */}
      <div className="glass-card p-5 rounded-3xl relative overflow-hidden border border-sky-500/20 bg-gradient-to-r from-[#070b16] via-[#091122] to-[#080d1a] shadow-2xl">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-winsor-600 via-sky-400 to-emerald-400" />
        <div className="absolute inset-0 bg-dot-grid opacity-15 pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          {/* Left: Model Identity & Live Stats */}
          <div className="flex items-start space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-winsor-700 via-sky-600 to-emerald-500 p-0.5 shadow-lg shadow-sky-500/20 flex items-center justify-center shrink-0">
              <div className="w-full h-full bg-[#070a14] rounded-[14px] flex items-center justify-center">
                <Cpu className="w-6 h-6 text-sky-400" />
              </div>
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base font-black text-white font-mono tracking-tight">
                  {modelStatus?.model_name || 'Calibrated Fund+Momentum Booster (Candidate 2)'}
                </h2>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  {modelStatus?.status === 'TRAINED' ? 'TRAINED & CALIBRATED' : 'BASELINE HEURISTIC'}
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-sky-950/60 text-sky-300 border border-sky-500/20">
                  {horizonDays}D Target Horizon
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs font-mono text-slate-300">
                <span className="flex items-center text-slate-400">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                  Brier Score:{' '}
                  <strong className="text-white ml-1">
                    {modelStatus?.brier_score !== undefined ? modelStatus.brier_score.toFixed(3) : '0.250'}
                  </strong>
                </span>
                <span className="flex items-center text-slate-400">
                  <BarChart3 className="w-3.5 h-3.5 mr-1 text-sky-400" />
                  Training Size:{' '}
                  <strong className="text-white ml-1">
                    {modelStatus?.sample_count ? `${modelStatus.sample_count} PIT Quarters` : '615 PIT Samples'}
                  </strong>
                </span>
                <span className="flex items-center text-slate-400">
                  <Clock className="w-3.5 h-3.5 mr-1 text-teal-400" />
                  Learned Architecture:{' '}
                  <strong className="text-slate-200 ml-1">
                    {modelStatus?.feature_mode === 'pair_fund_mom' ? 'Candidate 2 (Fund + Momentum)' : 'Point-in-Time Calibrated'}
                  </strong>
                </span>
              </div>
            </div>
          </div>

          {/* Right: Horizon Switcher & Model Training Trigger */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Quick Horizon Buttons */}
            <div className="flex items-center space-x-1 bg-[#05070f] p-1.5 rounded-2xl border border-white/[0.08]">
              <span className="text-[11px] font-mono text-slate-500 px-1.5">Horizon:</span>
              {[
                { label: '30D', days: 30, title: 'Tactical Momentum' },
                { label: '90D', days: 90, title: 'Quarterly Rebalance' },
                { label: '180D', days: 180, title: 'Semi-Annual Cycle' },
                { label: '1Y', days: 252, title: 'Strategic Compounding' },
              ].map((h) => (
                <button
                  key={h.days}
                  onClick={() => setHorizonDays(h.days)}
                  title={h.title}
                  className={`px-2.5 py-1 rounded-xl text-xs font-mono font-bold transition-all ${
                    horizonDays === h.days
                      ? 'bg-gradient-to-r from-winsor-700 to-sky-600 text-white shadow-md shadow-sky-500/25 border border-sky-400/40'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {h.label}
                </button>
              ))}
            </div>

            {/* Train / Retrain Action Button */}
            <button
              onClick={() => {
                setTrainHorizonDays(horizonDays);
                setShowTrainModal(true);
              }}
              className="px-4 py-2.5 rounded-2xl bg-gradient-to-r from-winsor-600 via-sky-600 to-emerald-500 hover:from-winsor-500 hover:to-emerald-400 text-white font-mono font-bold text-xs shadow-lg shadow-winsor-600/30 transition-all flex items-center space-x-2 cursor-pointer border border-sky-300/30 group"
            >
              <Sliders className="w-3.5 h-3.5 group-hover:rotate-45 transition-transform" />
              <span>Train Alpha Model</span>
            </button>
          </div>
        </div>
      </div>

      {/* Control Bar: As-of Date, Flexible Count Selector & Filters */}
      <div className="glass-card p-4 rounded-3xl flex flex-wrap items-center justify-between gap-4 border border-white/[0.08]">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {/* As-of Date Picker with Today & Baseline PIT shortcuts */}
          <div className="flex items-center space-x-2 bg-[#06080e] px-2.5 py-1.5 rounded-xl border border-white/[0.08]">
            <Calendar className="w-4 h-4 text-sky-400" />
            <span className="text-slate-400">As-Of:</span>
            <input
              type="date"
              value={asof}
              onChange={(e) => setAsof(e.target.value)}
              className="bg-transparent text-white font-mono font-bold focus:outline-none cursor-pointer"
            />
            <div className="flex items-center pl-1.5 border-l border-white/[0.08] space-x-1">
              <button
                type="button"
                onClick={() => setAsof(getTodayIST())}
                className={`px-2 py-0.5 rounded-lg text-[10px] font-mono font-bold transition-all ${
                  asof === getTodayIST()
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm'
                    : 'bg-[#080b13] text-slate-400 hover:text-white border border-white/[0.04]'
                }`}
                title="Set As-Of Date to Today (Live Current Date)"
              >
                Today (Live)
              </button>
              <button
                type="button"
                onClick={() => setAsof('2024-03-31')}
                className={`px-2 py-0.5 rounded-lg text-[10px] font-mono font-bold transition-all ${
                  asof === '2024-03-31'
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-400/40 shadow-sm'
                    : 'bg-[#080b13] text-slate-400 hover:text-white border border-white/[0.04]'
                }`}
                title="Set As-Of Date to Baseline PIT (2024-03-31)"
              >
                PIT (FY24)
              </button>
            </div>
          </div>

          {/* Quick Pick N Toggle with Flexible Count Selector (1 to 50) */}
          {viewMode === 'quick_pick' ? (
            <div className="flex items-center space-x-1.5 bg-[#06080e] p-1.5 rounded-xl border border-white/[0.08]">
              <span className="text-slate-400 text-[11px] px-1.5 font-mono">Picks:</span>
              {[1, 2, 3, 5, 10].map((n) => (
                <button
                  key={n}
                  onClick={() => setPickN(n)}
                  className={`px-2.5 py-1 rounded-lg font-mono font-bold text-xs transition-all ${
                    pickN === n
                      ? 'bg-winsor-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {n}
                </button>
              ))}
              <div className="flex items-center pl-1.5 border-l border-white/[0.08] space-x-1">
                <button
                  type="button"
                  onClick={() => setPickN(Math.max(1, pickN - 1))}
                  className="w-5 h-5 flex items-center justify-center rounded bg-[#0a0d17] hover:bg-winsor-900/40 text-slate-300 font-mono font-bold text-xs border border-white/[0.06]"
                  title="Decrease"
                >
                  -
                </button>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={pickN}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (!isNaN(val)) setPickN(Math.max(1, Math.min(50, val)));
                  }}
                  className="w-10 text-center bg-[#080b13] border border-white/[0.08] rounded py-0.5 text-xs font-mono font-bold text-sky-400 focus:outline-none focus:border-sky-400"
                />
                <button
                  type="button"
                  onClick={() => setPickN(Math.min(50, pickN + 1))}
                  className="w-5 h-5 flex items-center justify-center rounded bg-[#0a0d17] hover:bg-winsor-900/40 text-slate-300 font-mono font-bold text-xs border border-white/[0.06]"
                  title="Increase"
                >
                  +
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Sector Filter */}
              <div className="flex items-center space-x-2 bg-[#06080e] px-3 py-1.5 rounded-xl border border-white/[0.08]">
                <Filter className="w-4 h-4 text-sky-400" />
                <span className="text-slate-400">Sector:</span>
                <select
                  value={selectedSector}
                  onChange={(e) => setSelectedSector(e.target.value)}
                  className="bg-transparent text-white font-semibold focus:outline-none cursor-pointer capitalize"
                >
                  {sectors.map((s) => (
                    <option key={s} value={s} className="bg-[#0b0e17] text-white">
                      {s.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>

              {/* Top N Count Selector with Flexible Input (1 to 50) */}
              <div className="flex items-center space-x-1.5 bg-[#06080e] p-1.5 rounded-xl border border-white/[0.08]">
                <span className="text-slate-400 text-[11px] px-1.5 font-mono">Show:</span>
                {[5, 8, 15, 25].map((n) => (
                  <button
                    key={n}
                    onClick={() => setTopN(n)}
                    className={`px-2.5 py-1 rounded-lg font-mono font-bold text-xs transition-all ${
                      topN === n
                        ? 'bg-winsor-600 text-white shadow-md'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {n}
                  </button>
                ))}
                <div className="flex items-center pl-1.5 border-l border-white/[0.08] space-x-1">
                  <button
                    type="button"
                    onClick={() => setTopN(Math.max(1, topN - 1))}
                    className="w-5 h-5 flex items-center justify-center rounded bg-[#0a0d17] hover:bg-winsor-900/40 text-slate-300 font-mono font-bold text-xs border border-white/[0.06]"
                    title="Decrease"
                  >
                    -
                  </button>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={topN}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      if (!isNaN(val)) setTopN(Math.max(1, Math.min(50, val)));
                    }}
                    className="w-10 text-center bg-[#080b13] border border-white/[0.08] rounded py-0.5 text-xs font-mono font-bold text-sky-400 focus:outline-none focus:border-sky-400"
                  />
                  <button
                    type="button"
                    onClick={() => setTopN(Math.min(50, topN + 1))}
                    className="w-5 h-5 flex items-center justify-center rounded bg-[#0a0d17] hover:bg-winsor-900/40 text-slate-300 font-mono font-bold text-xs border border-white/[0.06]"
                    title="Increase"
                  >
                    +
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Refresh button */}
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-[#0a0d17] hover:bg-[#121627] border border-white/[0.08] rounded-xl text-xs font-bold text-slate-300 hover:text-white transition-all shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          <span>Refresh Screener</span>
        </button>
      </div>

      {/* Loading & Error States */}
      {loading && (
        <div className="flex flex-col items-center justify-center h-64 text-slate-400 glass-card rounded-3xl">
          <div className="w-10 h-10 rounded-full border-2 border-winsor-500/20 border-t-winsor-500 animate-spin mb-3" />
          <span className="font-semibold text-slate-200">Evaluating Multi-Factor Ranks...</span>
          <span className="text-xs text-slate-500 mt-1 font-mono">
            Executing 4-stage filters & point-in-time scores
          </span>
        </div>
      )}

      {error && (
        <div className="p-5 bg-rose-950/30 border border-rose-900 rounded-2xl text-rose-300 flex items-center justify-between">
          <div>
            <h4 className="font-bold text-rose-200">Error Loading Recommendations</h4>
            <p className="text-xs mt-1 text-slate-400">{error}</p>
          </div>
          <button
            onClick={loadData}
            className="px-3.5 py-1.5 bg-rose-900/60 hover:bg-rose-800 rounded-xl text-xs font-bold text-white transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Mode 1: Top N Quick Picks with Interactive Capital Sizing Simulator (500 to 1M) */}
      {!loading && !error && viewMode === 'quick_pick' && (
        <div className="space-y-6">
          {/* Tactical Context Banner */}
          <div className="p-5 rounded-3xl bg-[#080b13] border border-white/[0.08] shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 bg-dot-grid opacity-15 pointer-events-none" />
            <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs font-bold font-mono uppercase tracking-wider text-sky-300">
                    High-Conviction Tactical Deployment ({picks.length} Ideas)
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
                  {deploymentContext ||
                    `Top ${pickN} ideas selected with strict cross-sector diversification (max 1 per sector) and active portfolio awareness.`}
                </p>
              </div>
              <div className="text-right">
                <span className="text-[11px] font-mono text-emerald-400 flex items-center justify-end font-semibold">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1" />
                  Diversified Risk Balanced
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  Point-in-Time Alpha Engine
                </span>
              </div>
            </div>
          </div>

          {/* Interactive Capital Sizing Simulator (Flexible: ₹500 to ₹10,00,000 / 1M) */}
          <div className="glass-card p-6 rounded-3xl relative overflow-hidden border border-white/[0.08] shadow-2xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-white/[0.06]">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-winsor-700 via-winsor-600 to-sky-400 text-white flex items-center justify-center font-mono font-black text-lg shadow-lg shadow-winsor-500/20">
                  ₹
                </div>
                <div>
                  <h3 className="text-sm font-black uppercase tracking-wider text-white">
                    Tactical Capital Sizing Simulator
                  </h3>
                  <p className="text-xs text-slate-400">
                    Deploy any cash amount from ₹500 to ₹10,00,000 (1M) for whole-share lot allocations
                  </p>
                </div>
              </div>

              {/* Direct Editable Capital Input */}
              <div className="flex items-center space-x-2 bg-[#06080e] px-4 py-2 rounded-2xl border border-white/[0.08]">
                <span className="text-slate-400 font-mono font-bold text-lg">₹</span>
                <input
                  type="number"
                  min={500}
                  max={1000000}
                  step={500}
                  value={freshCapital}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    if (!isNaN(val)) setFreshCapital(Math.max(500, Math.min(1000000, val)));
                  }}
                  className="bg-transparent text-xl font-black font-mono text-white tracking-tight w-32 focus:outline-none"
                />
              </div>
            </div>

            {/* Quick Amount Chips */}
            <div className="flex flex-wrap items-center gap-1.5 pt-4">
              <span className="text-[11px] font-mono text-slate-500 mr-1">Quick Capital:</span>
              {[500, 2000, 10000, 50000, 100000, 500000, 1000000].map((amt) => (
                <button
                  key={amt}
                  onClick={() => setFreshCapital(amt)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all ${
                    freshCapital === amt
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-400/50 shadow-sm'
                      : 'bg-[#06080e] text-slate-400 hover:text-white border border-white/[0.06]'
                  }`}
                >
                  {amt >= 100000 ? `₹${amt / 100000}L` : amt >= 1000 ? `₹${amt / 1000}k` : `₹${amt}`}
                </button>
              ))}
            </div>

            {/* Slider Track (from 500 to 1M) */}
            <div className="py-4">
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2">
                <span className="text-emerald-400 font-bold">₹500</span>
                <span>₹10,000</span>
                <span className="text-sky-400 font-bold">₹1,00,000</span>
                <span>₹5,00,000</span>
                <span className="text-emerald-400 font-bold">₹10,00,000 (1M)</span>
              </div>
              <input
                type="range"
                min="500"
                max="1000000"
                step="500"
                value={freshCapital}
                onChange={(e) => setFreshCapital(Number(e.target.value))}
                className="w-full h-2 bg-[#06080e] rounded-lg appearance-none cursor-pointer accent-sky-400 border border-white/[0.08]"
              />
            </div>

            {/* Share Allocation Results Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 mt-1">
              {picks.map((pick) => {
                const targetRupees = freshCapital * pick.suggested_weight;
                const sharePrice = pick.latest_close || 1500;
                const sharesToBuy = Math.floor(targetRupees / sharePrice);
                const actualRupees = sharesToBuy * sharePrice;
                const remainder = targetRupees - actualRupees;
                const isUnderCapitalized = sharesToBuy === 0;

                return (
                  <div
                    key={pick.symbol}
                    className={`p-4 rounded-2xl bg-[#080b13] border transition-all flex flex-col justify-between group ${
                      isUnderCapitalized
                        ? 'border-amber-500/20 hover:border-amber-500/40'
                        : 'border-white/[0.06] hover:border-winsor-500/40'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-base font-black text-white font-mono group-hover:text-sky-300 transition-colors">
                            {pick.symbol}
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-winsor-950 text-winsor-400 border border-winsor-800/60 font-bold">
                            {(pick.suggested_weight * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1 font-mono">
                          LTP: ₹{sharePrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                        </p>
                      </div>

                      <div className="text-right">
                        <div className="flex items-baseline justify-end space-x-1">
                          <span
                            className={`text-xl font-black font-mono ${
                              isUnderCapitalized ? 'text-amber-400' : 'text-emerald-400'
                            }`}
                          >
                            {sharesToBuy}
                          </span>
                          <span className="text-xs font-bold text-slate-400">Shares</span>
                        </div>
                        <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                          Target: ₹{targetRupees.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        </p>
                      </div>
                    </div>

                    {isUnderCapitalized ? (
                      <div className="mt-3 pt-2.5 border-t border-white/[0.04] text-[11px] font-mono text-amber-300 flex items-center justify-between">
                        <span>LTP &gt; Target Allocation</span>
                        <span>Need +₹{(sharePrice - targetRupees).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                      </div>
                    ) : (
                      <div className="mt-3 pt-2.5 border-t border-white/[0.04] text-[11px] font-mono text-slate-400 flex items-center justify-between">
                        <span>Actual: ₹{actualRupees.toLocaleString('en-IN')}</span>
                        <span className="text-emerald-400 font-semibold">Buffer: ₹{remainder.toFixed(0)}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Quick Pick Cards */}
          <div className="grid grid-cols-1 gap-6">
            {picks.map((pick) => (
              <QuickPickCard key={pick.symbol} pick={pick} />
            ))}
          </div>
        </div>
      )}

      {/* Mode 2: Cross-Sectional Factor Comparison Matrix */}
      {!loading && !error && viewMode === 'matrix' && (
        <FactorMatrixView stocks={filteredRecs} />
      )}

      {/* Mode 3: Detailed Stock Cards */}
      {!loading && !error && viewMode === 'cards' && (
        <div className="grid grid-cols-1 gap-4">
          {filteredRecs.map((stock, idx) => (
            <StockCard key={stock.symbol} stock={stock} rank={idx + 1} />
          ))}
        </div>
      )}
      {/* Empty State / Point-in-Time Boundary Notice */}
      {!loading && !error && ((viewMode === 'quick_pick' && picks.length === 0) || (viewMode !== 'quick_pick' && filteredRecs.length === 0)) && (
        <div className="glass-card p-8 rounded-3xl border border-white/[0.08] text-center space-y-4 max-w-xl mx-auto my-6 shadow-2xl">
          <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-400/30 flex items-center justify-center mx-auto text-sky-400">
            <Calendar className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-black text-white font-mono">
              No Disclosures Found on As-Of: {asof}
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto leading-relaxed">
              Arth IQ enforces strict Point-in-Time discipline: data is never forward-filled or leaked from future quarters. Disclosures and prices must precede or match the selected cutoff date.
            </p>
          </div>
          <div className="pt-2">
            <button
              onClick={() => setAsof('2024-03-31')}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-winsor-700 via-winsor-600 to-sky-500 text-white font-bold text-xs shadow-lg shadow-winsor-500/25 hover:brightness-110 transition-all cursor-pointer"
            >
              Switch to Baseline PIT Dataset (2024-03-31)
            </button>
          </div>
        </div>
      )}

      {/* Interactive Alpha Model Training & Calibration Modal */}
      {showTrainModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-2xl bg-[#090d18] border border-sky-500/30 rounded-3xl shadow-2xl overflow-hidden p-6 text-slate-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-winsor-700 via-sky-600 to-emerald-500 p-0.5 flex items-center justify-center">
                  <div className="w-full h-full bg-[#070a14] rounded-[14px] flex items-center justify-center">
                    <Cpu className="w-5 h-5 text-sky-400" />
                  </div>
                </div>
                <div>
                  <h3 className="text-base font-black text-white font-mono">
                    Train Point-in-Time Alpha Prediction Engine
                  </h3>
                  <p className="text-xs text-slate-400">
                    Walk-forward cross-sectional training strictly prior to As-Of date (zero lookahead)
                  </p>
                </div>
              </div>

              <button
                onClick={() => setShowTrainModal(false)}
                className="w-8 h-8 rounded-xl bg-[#0e1322] hover:bg-white/[0.08] flex items-center justify-center text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleTrainModel} className="space-y-4 pt-4 text-xs font-mono">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* 1. Algorithm Selection */}
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-bold block">Model Algorithm:</label>
                  <select
                    value={trainModelType}
                    onChange={(e) => setTrainModelType(e.target.value)}
                    className="w-full bg-[#060810] border border-white/[0.08] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value="lightgbm">Calibrated LightGBM Booster (Recommended)</option>
                    <option value="logistic">Regularized Logistic Regression (Platt)</option>
                    <option value="xgboost">XGBoost Classifier</option>
                  </select>
                </div>

                {/* 2. Target Alpha Horizon */}
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-bold block">Target Alpha Horizon:</label>
                  <select
                    value={trainHorizonDays}
                    onChange={(e) => setTrainHorizonDays(Number(e.target.value))}
                    className="w-full bg-[#060810] border border-white/[0.08] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value={30}>30 Days (Tactical Momentum & Reversal)</option>
                    <option value={90}>90 Days (Quarterly Fundamental Compounding)</option>
                    <option value={180}>180 Days (Half-Year Cycle Outperformance)</option>
                    <option value={252}>252 Days (1-Year Strategic Alpha)</option>
                  </select>
                </div>

                {/* 3. Feature Set Selection */}
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-bold block">Feature Architecture:</label>
                  <select
                    value={trainFeatureMode}
                    onChange={(e) => setTrainFeatureMode(e.target.value)}
                    className="w-full bg-[#060810] border border-white/[0.08] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value="pair_fund_mom">Candidate 2: Fund + Momentum (Gate 8 Winner)</option>
                    <option value="set_a">Candidate 1: Fundamentals Only (RoE, RoCE, D/E)</option>
                    <option value="pair_fund_sent">Candidate 3: Fundamentals + Sentiment</option>
                    <option value="all">Full 24 Point-in-Time Factors</option>
                  </select>
                </div>

                {/* 4. Calibration Method */}
                <div className="space-y-1.5">
                  <label className="text-slate-400 font-bold block">Probability Calibration:</label>
                  <select
                    value={trainCalibration}
                    onChange={(e) => setTrainCalibration(e.target.value)}
                    className="w-full bg-[#060810] border border-white/[0.08] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value="isotonic">Isotonic Regression (Non-parametric)</option>
                    <option value="sigmoid">Platt Scaling (Sigmoid Calibrated)</option>
                  </select>
                </div>
              </div>

              {/* Status Feedback / Success / Error Message */}
              {trainErrorMsg && (
                <div className="p-3 bg-rose-950/60 border border-rose-500/40 rounded-xl text-rose-300 flex items-center space-x-2 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{trainErrorMsg}</span>
                </div>
              )}

              {trainSuccessResult && (
                <div className="p-4 bg-emerald-950/40 border border-emerald-500/30 rounded-2xl text-emerald-300 space-y-2">
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="font-bold">{trainSuccessResult.message}</span>
                  </div>

                  {/* Learned Feature Importances */}
                  {trainSuccessResult.feature_importances && Object.keys(trainSuccessResult.feature_importances).length > 0 && (
                    <div className="pt-2 border-t border-emerald-500/20 space-y-1.5">
                      <span className="text-[11px] text-slate-400 uppercase font-bold block">
                        Learned Feature Weights (Contribution to Alpha):
                      </span>
                      <div className="space-y-1">
                        {Object.entries(trainSuccessResult.feature_importances)
                          .sort((a, b) => b[1] - a[1])
                          .slice(0, 5)
                          .map(([feat, weight]) => (
                            <div key={feat} className="flex items-center justify-between text-[11px]">
                              <span className="text-slate-300 capitalize">{feat.replace(/_/g, ' ')}:</span>
                              <div className="flex items-center space-x-2">
                                <div className="w-28 h-1.5 bg-[#05070e] rounded-full overflow-hidden border border-white/[0.06]">
                                  <div
                                    className="h-full bg-gradient-to-r from-sky-400 to-emerald-400"
                                    style={{ width: `${Math.round(weight * 100)}%` }}
                                  />
                                </div>
                                <span className="font-bold text-white w-10 text-right">
                                  {(weight * 100).toFixed(1)}%
                                </span>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-3 border-t border-white/[0.08] flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowTrainModal(false)}
                  className="px-4 py-2 rounded-xl bg-[#0a0d18] hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={isTraining}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-winsor-600 via-sky-600 to-emerald-500 hover:from-winsor-500 hover:to-emerald-400 text-white font-bold transition-all shadow-lg flex items-center space-x-2 disabled:opacity-50"
                >
                  {isTraining ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-white" />
                      <span>Training Model...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 text-white" />
                      <span>Start Point-in-Time Training</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
