import React, { useState, useEffect } from 'react';
import {
  BrainCircuit,
  Play,
  CheckCircle2,
  AlertCircle,
  RotateCw,
  BarChart3,
  Sliders,
  ShieldCheck,
} from 'lucide-react';
import { fetchModelStatus, trainModel } from '../api/client';
import { ModelStatusResponse, ModelTrainResponse } from '../types/api';

export const ModelTrainingView: React.FC = () => {
  const [status, setStatus] = useState<ModelStatusResponse | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [isTraining, setIsTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<ModelTrainResponse | null>(null);
  const [trainError, setTrainError] = useState<string | null>(null);

  // Form parameters
  const [modelType, setModelType] = useState<string>('lightgbm');
  const [horizonDays, setHorizonDays] = useState<number>(90);
  const [featureMode, setFeatureMode] = useState<string>('pair_fund_mom');
  const [calibrationMethod, setCalibrationMethod] = useState<string>('platt');

  const loadStatus = async () => {
    setIsLoadingStatus(true);
    try {
      const res = await fetchModelStatus();
      setStatus(res);
    } catch {
      // ignore
    } finally {
      setIsLoadingStatus(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleTrainSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsTraining(true);
    setTrainError(null);
    setTrainResult(null);

    try {
      const res = await trainModel({
        model_type: modelType,
        horizon_days: horizonDays,
        feature_mode: featureMode,
        calibration_method: calibrationMethod,
      });
      setTrainResult(res);
      await loadStatus();
    } catch (err: any) {
      setTrainError(err.message || 'Model training failed');
    } finally {
      setIsTraining(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Header Banner */}
      <div className="p-6 rounded-3xl bg-[#080c18] border border-white/[0.08] relative overflow-hidden flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs text-sky-400 font-mono mb-1">
            <BrainCircuit className="w-4 h-4" />
            <span>INSTITUTIONAL QUANTITATIVE ML</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Alpha Prediction & Calibration Engine
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-xl">
            Train, calibrate, and promote point-in-time machine learning models for excess forward equity returns under zero-lookahead guarantees.
          </p>
        </div>

        <button
          onClick={loadStatus}
          disabled={isLoadingStatus}
          className="p-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 hover:text-white transition-all cursor-pointer self-start sm:self-auto"
          title="Refresh status"
        >
          <RotateCw className={`w-4 h-4 ${isLoadingStatus ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Model Operational Status Card */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08]">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider mb-1">
            Model State
          </div>
          <div className="text-xl font-black text-white font-mono flex items-center space-x-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                status?.is_trained ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}
            />
            <span>{status?.status || (isLoadingStatus ? 'Loading...' : 'BASELINE')}</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            {status?.model_name || 'Heuristic Scoring Baseline'}
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08]">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider mb-1">
            Target Alpha Horizon
          </div>
          <div className="text-xl font-black text-white font-mono">
            {status?.horizon_days ? `${status.horizon_days} Days` : '90 Days'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            Quarterly Outperformance
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08]">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider mb-1">
            Training Observations
          </div>
          <div className="text-xl font-black text-white font-mono">
            {status?.sample_count ? status.sample_count.toLocaleString() : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            PIT Historical Snapshots
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08]">
          <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider mb-1">
            Calibration Brier Score
          </div>
          <div className="text-xl font-black text-emerald-400 font-mono">
            {status?.brier_score !== undefined ? status.brier_score.toFixed(3) : '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            Target: &lt; 0.220 (Well-Calibrated)
          </div>
        </div>
      </div>

      {/* Main Grid: Training Form + Feature Importance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Training Configuration Form */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 sm:p-8 rounded-3xl bg-[#080c18] border border-white/[0.08]">
            <h2 className="text-base font-bold text-white mb-2 flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-sky-400" />
              <span>Model Hyperparameter & Feature Architecture</span>
            </h2>
            <p className="text-xs text-slate-400 mb-6">
              Configure point-in-time training specifications. Once trained, newly short-listed alpha recommendations will automatically reflect the retrained booster.
            </p>

            <form onSubmit={handleTrainSubmit} className="space-y-5 text-xs font-mono">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* 1. Algorithm */}
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-bold block">Model Algorithm:</label>
                  <select
                    value={modelType}
                    onChange={(e) => setModelType(e.target.value)}
                    className="w-full bg-[#0d1222] border border-white/[0.08] rounded-xl px-3 py-2.5 text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value="lightgbm">Calibrated LightGBM Booster (Recommended)</option>
                    <option value="logistic">Regularized Logistic Regression (Platt)</option>
                    <option value="xgboost">XGBoost Classifier</option>
                  </select>
                </div>

                {/* 2. Horizon */}
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-bold block">Alpha Forecast Horizon:</label>
                  <select
                    value={horizonDays}
                    onChange={(e) => setHorizonDays(Number(e.target.value))}
                    className="w-full bg-[#0d1222] border border-white/[0.08] rounded-xl px-3 py-2.5 text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value={30}>30 Days (Tactical Momentum & Reversal)</option>
                    <option value={90}>90 Days (Quarterly Fundamental Compounding)</option>
                    <option value={180}>180 Days (Half-Year Cycle Outperformance)</option>
                    <option value={252}>252 Days (1-Year Strategic Alpha)</option>
                  </select>
                </div>

                {/* 3. Feature Set */}
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-bold block">Feature Architecture:</label>
                  <select
                    value={featureMode}
                    onChange={(e) => setFeatureMode(e.target.value)}
                    className="w-full bg-[#0d1222] border border-white/[0.08] rounded-xl px-3 py-2.5 text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value="pair_fund_mom">Candidate 2: Fund + Momentum (Gate 8 Winner)</option>
                    <option value="set_a">Candidate 1: Fundamentals Only (RoE, RoCE, D/E)</option>
                    <option value="pair_fund_sent">Candidate 3: Fundamentals + Sentiment</option>
                    <option value="all">Full 24 Point-in-Time Factors</option>
                  </select>
                </div>

                {/* 4. Calibration Method */}
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-bold block">Calibration Method:</label>
                  <select
                    value={calibrationMethod}
                    onChange={(e) => setCalibrationMethod(e.target.value)}
                    className="w-full bg-[#0d1222] border border-white/[0.08] rounded-xl px-3 py-2.5 text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value="platt">Platt Scaling (Sigmoid Normalization)</option>
                    <option value="isotonic">Isotonic Non-Parametric Regression</option>
                  </select>
                </div>
              </div>

              {/* Error / Success Notifications */}
              {trainError && (
                <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{trainError}</span>
                </div>
              )}

              {trainResult && (
                <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 space-y-1">
                  <div className="flex items-center space-x-2 font-bold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>{trainResult.message}</span>
                  </div>
                  <div className="text-[11px] text-emerald-400/80">
                    Trained on {trainResult.sample_count} samples | Brier Score: {trainResult.brier_score.toFixed(3)} | Accuracy: {(trainResult.train_accuracy * 100).toFixed(1)}%
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={isTraining}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-sky-500 via-blue-500 to-indigo-500 hover:from-sky-400 hover:to-indigo-400 text-white font-bold text-xs shadow-[0_0_25px_rgba(14,165,233,0.35)] transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-60"
              >
                {isTraining ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Training Point-in-Time Alpha Booster...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>Train & Promote Alpha Model</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Right Column (1 Col): Feature Importances & Model Guarantees */}
        <div className="space-y-6">
          <div className="p-6 rounded-3xl bg-[#080c18] border border-white/[0.08]">
            <h3 className="text-sm font-bold text-white mb-3 flex items-center space-x-2">
              <BarChart3 className="w-4 h-4 text-sky-400" />
              <span>Feature Importances</span>
            </h3>

            {status?.feature_importances && Object.keys(status.feature_importances).length > 0 ? (
              <div className="space-y-2.5 font-mono text-xs">
                {Object.entries(status.feature_importances)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 7)
                  .map(([name, weight]) => (
                    <div key={name}>
                      <div className="flex justify-between text-[11px] text-slate-300 mb-1">
                        <span className="truncate pr-2">{name}</span>
                        <span className="text-sky-400 font-bold">{(weight * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-sky-500 to-blue-400 rounded-full"
                          style={{ width: `${Math.min(100, Math.max(5, weight * 100))}%` }}
                        />
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500 font-mono p-4 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                Feature weights will populate upon model execution.
              </div>
            )}
          </div>

          <div className="p-5 rounded-2xl bg-[#080c18] border border-white/[0.08] text-xs font-mono space-y-2 text-slate-400">
            <div className="text-[11px] text-emerald-400 font-bold uppercase tracking-wider flex items-center space-x-1.5 mb-2">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Institutional Gates</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              • Strict Point-in-Time effective date filtering guarantees zero future information leakage.
            </p>
            <p className="text-[11px] leading-relaxed">
              • Platt calibration aligns probabilities with empirical win rates for Kelly & HRP tilt weights.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
