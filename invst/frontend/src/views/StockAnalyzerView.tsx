import React, { useState, useEffect } from 'react';
import {
  Search,
  ShieldCheck,
  AlertTriangle,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Target,
  FileText,
  Radio,
  Layers,
  HelpCircle,
  Compass,
  CheckCircle2,
  AlertCircle,
  BookmarkPlus,
  ExternalLink,
  X,
  Sparkles,
} from 'lucide-react';
import { FactorRadarChart } from '../components/FactorRadarChart';
import { PriceRangeLadder } from '../components/PriceRangeLadder';
import {
  analyzeStock,
  fetchMacroPulse,
  fetchPortfolios,
  createPortfolio,
  addStockToPortfolio,
} from '../api/client';
import {
  FullStockAnalysisResponse,
  MacroPulseResponse,
  PortfolioSummary,
} from '../types/api';

interface StockAnalyzerViewProps {
  onNavigateTab?: (tab: string) => void;
  initialSymbol?: string;
}

export const StockAnalyzerView: React.FC<StockAnalyzerViewProps> = ({ onNavigateTab, initialSymbol }) => {
  const [symbol, setSymbol] = useState(initialSymbol || 'TCS');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<FullStockAnalysisResponse | null>(null);
  const [pulse, setPulse] = useState<MacroPulseResponse | null>(null);
  const [activeThesisTab, setActiveThesisTab] = useState<'exec' | 'moat' | 'val' | 'tech' | 'tactical'>('exec');
  const [activeScoreDetail, setActiveScoreDetail] = useState<string | null>(null);
  const [fetchLiveQuotes, setFetchLiveQuotes] = useState(true);

  // Add to Target List / Portfolio Modal State
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedDestId, setSelectedDestId] = useState<string>('targetlist_dips');
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [newListName, setNewListName] = useState('');
  const [newListType, setNewListType] = useState<'PORTFOLIO' | 'TARGETLIST'>('TARGETLIST');
  const [newListDescription, setNewListDescription] = useState('');
  const [addShares, setAddShares] = useState('10');
  const [addPrice, setAddPrice] = useState('');
  const [addNotes, setAddNotes] = useState('');
  const [isSubmittingAdd, setIsSubmittingAdd] = useState(false);
  const [addModalError, setAddModalError] = useState<string | null>(null);
  const [toastNotification, setToastNotification] = useState<{
    message: string;
    portfolioId: string;
    portfolioName: string;
  } | null>(null);

  const quickPicks = ['TCS', 'INFY', 'RELIANCE', 'HDFCBANK', 'NIFTYBEES', 'GOLDBEES', 'BAJFINANCE', 'TITAN'];

  useEffect(() => {
    fetchMacroPulse().then(setPulse).catch(() => {});
    loadPortfolios();
    handleAnalyze(initialSymbol || symbol || 'TCS');
  }, [initialSymbol]);

  const loadPortfolios = async () => {
    try {
      const list = await fetchPortfolios();
      setPortfolios(list);
      if (list.length > 0 && !list.some((p) => p.id === selectedDestId)) {
        const targetList = list.find((p) => p.portfolio_type === 'TARGETLIST');
        setSelectedDestId(targetList ? targetList.id : list[0].id);
      }
    } catch {
      // Ignore background load error
    }
  };

  const handleOpenAddModal = () => {
    if (!data) return;
    loadPortfolios();

    // Default price: dip target price if positive, else live current price
    const defaultPrice =
      data.tactical_action?.dip_target_price && data.tactical_action.dip_target_price > 0
        ? data.tactical_action.dip_target_price
        : data.current_price;
    setAddPrice(defaultPrice.toFixed(1));

    if (!addShares || addShares === '0') {
      setAddShares('10');
    }

    // Prefill notes with concise actionable conviction
    const notesSummary = `${data.verdict_badge} (${data.investment_score.toFixed(0)}/100). ${
      data.tactical_action?.dip_target_price
        ? `Dip Target: ₹${data.tactical_action.dip_target_price} (-${data.tactical_action.dip_discount_pct}%). `
        : ''
    }${data.tactical_action?.verdict_reasoning ? data.tactical_action.verdict_reasoning.slice(0, 160) : ''}`;
    setAddNotes(notesSummary);
    setAddModalError(null);
    setIsCreatingNew(false);
    setIsAddModalOpen(true);
  };

  const handleConfirmAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data) return;

    const sh = parseFloat(addShares);
    const pr = parseFloat(addPrice);
    if (isNaN(sh) || sh <= 0) {
      setAddModalError('Please enter a valid share quantity greater than 0.');
      return;
    }
    if (isNaN(pr) || pr <= 0) {
      setAddModalError('Please enter a valid price greater than 0.');
      return;
    }

    setIsSubmittingAdd(true);
    setAddModalError(null);

    try {
      let destId = selectedDestId;
      let destName = portfolios.find((p) => p.id === selectedDestId)?.name || 'Target List';

      if (isCreatingNew) {
        if (!newListName.trim()) {
          setAddModalError('Please provide a name for the new list or portfolio.');
          setIsSubmittingAdd(false);
          return;
        }
        const created = await createPortfolio({
          name: newListName.trim(),
          description: newListDescription.trim() || undefined,
          portfolio_type: newListType,
        });
        destId = created.id;
        destName = created.name;
        await loadPortfolios();
      }

      await addStockToPortfolio(destId, {
        symbol: data.symbol,
        shares: sh,
        buy_price: pr,
        target_price: data.tactical_action?.dip_target_price || pr,
        notes: addNotes.trim() || undefined,
      });

      setIsAddModalOpen(false);
      setToastNotification({
        message: `Successfully added ${data.symbol} (${sh} shares @ ₹${pr.toFixed(1)}) to "${destName}"`,
        portfolioId: destId,
        portfolioName: destName,
      });

      // Clear toast after 8s
      setTimeout(() => {
        setToastNotification(null);
      }, 8000);
    } catch (err: any) {
      setAddModalError(err.message || 'Failed to add stock to list.');
    } finally {
      setIsSubmittingAdd(false);
    }
  };

  const handleAnalyze = async (tickerToAnalyze: string, forceLive?: boolean) => {
    const sym = tickerToAnalyze.trim().toUpperCase();
    if (!sym) return;
    setLoading(true);
    setError(null);
    try {
      const isLive = forceLive !== undefined ? forceLive : fetchLiveQuotes;
      const res = await analyzeStock(sym, isLive);
      setData(res);
      setSymbol(sym);
      setActiveThesisTab('exec');
    } catch (err: any) {
      setError(err.message || `No stock or ETF found for symbol "${sym}". Please verify the ticker symbol.`);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn pb-16">
      {/* 1. Header Banner & Macro Pulse */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-3xl bg-gradient-to-r from-[#0d1222] via-[#090d19] to-[#0d1222] border border-white/[0.08] shadow-2xl">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              <Search className="w-6 h-6 text-amber-400" />
              Stock & ETF Institutional Analyzer
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
              INSTITUTIONAL PM V2
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Senior-grade equity & ETF diagnosis • Actionable buy/dip levels • Transparent score explanations • Reverse-DCF expectations
          </p>
        </div>

        {pulse && (
          <div className="flex items-center space-x-3 px-4 py-2 rounded-2xl bg-white/[0.03] border border-white/[0.06] font-mono text-xs">
            <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
            <div>
              <span className="text-slate-400">India VIX: </span>
              <span className="font-bold text-white">{pulse.india_vix.toFixed(2)}</span>
            </div>
            <div className="w-px h-4 bg-white/10" />
            <div>
              <span className="text-slate-400">Regime: </span>
              <span
                className={`font-bold px-2 py-0.5 rounded-full text-[10px] ${
                  pulse.regime === 'HIGH_VOLATILITY'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                    : pulse.regime === 'EXPANSIONARY'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                }`}
              >
                {pulse.regime}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 2. Search & Quick Ticker Selection */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAnalyze(symbol);
          }}
          className="flex-1 flex items-center relative w-full"
        >
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="Enter Stock or ETF Symbol (e.g. TCS, RELIANCE, NIFTYBEES, GOLDBEES)..."
            className="w-full pl-11 pr-32 py-3 bg-[#080c16] border border-white/[0.1] rounded-2xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-400/60 focus:ring-1 focus:ring-amber-400/30 transition-all font-mono uppercase"
          />
          <Search className="w-5 h-5 text-slate-400 absolute left-3.5" />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-2 px-4 py-1.5 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-400 text-slate-950 font-bold text-xs hover:brightness-110 transition-all cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
        </form>

        <div className="flex items-center gap-1.5 flex-wrap w-full sm:w-auto">
          <span className="text-[11px] font-mono text-slate-400 mr-1">Quick Picks:</span>
          {quickPicks.map((q) => (
            <button
              key={q}
              onClick={() => handleAnalyze(q)}
              className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all ${
                symbol === q
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-white/[0.03] text-slate-400 hover:text-white border border-white/[0.05]'
              }`}
            >
              {q}
            </button>
          ))}
          {data && (
            <button
              onClick={handleOpenAddModal}
              className="ml-2 px-3 py-1 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
              title="Add current stock to Wishlist / Target List"
            >
              <BookmarkPlus className="w-3.5 h-3.5 text-amber-400" />
              <span>+ Wishlist</span>
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between px-1">
        <label className="flex items-center gap-2 text-slate-400 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={fetchLiveQuotes}
            onChange={(e) => {
              const checked = e.target.checked;
              setFetchLiveQuotes(checked);
              fetchMacroPulse(checked).then(setPulse).catch(() => {});
            }}
            className="rounded border-slate-700 bg-slate-900 text-amber-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
          />
          <span className="text-[11px] font-mono">Fetch Live Quotes (yfinance)</span>
          <span className="text-[10px] text-slate-500 font-mono">(Defaults to fast local DB)</span>
        </label>
      </div>

      {error && (
        <div className="p-5 rounded-2xl bg-rose-950/30 border border-rose-500/30 text-rose-300 text-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <div className="font-semibold text-white">{error}</div>
              <div className="text-xs text-rose-300/80 font-mono mt-0.5">
                Ensure the symbol matches a valid NSE/BSE ticker (e.g. TCS, INFY, RELIANCE, SILVERIETF, GOLDBEES).
              </div>
            </div>
          </div>
          <button
            onClick={() => handleAnalyze('TCS')}
            className="px-3 py-1.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.12] text-xs font-mono text-slate-300 transition-all border border-white/10 shrink-0 self-start sm:self-center cursor-pointer"
          >
            Reset to TCS
          </button>
        </div>
      )}

      {loading && (
        <div className="p-16 flex flex-col items-center justify-center space-y-3">
          <div className="w-10 h-10 border-2 border-amber-500/20 border-t-amber-400 rounded-full animate-spin" />
          <p className="text-xs font-mono text-slate-400">Conducting institutional research, trend audit & scenario forecast...</p>
        </div>
      )}

      {data && !loading && (
        <>
          {/* 3. Stock Identity & Technical Overview Card */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-[#090d19] border border-white/[0.08] space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-400 uppercase">Instrument Symbol</span>
                {data.is_etf && (
                  <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    ETF / BASKET
                  </span>
                )}
              </div>
              <div className="text-2xl font-black text-white">{data.symbol}</div>
              <div className="text-xs text-slate-300 truncate font-medium">{data.company_name}</div>
              <span className="inline-block text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20 mt-1">
                {data.sector.replace('_', ' ').toUpperCase()} • {data.sector_archetype}
              </span>
            </div>

            <div className="p-5 rounded-2xl bg-[#090d19] border border-white/[0.08] space-y-1">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Live Quote / CMP</span>
              <div className="text-2xl font-black text-white">₹{data.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
              <div className={`text-xs font-mono font-bold flex items-center gap-1 ${data.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {data.change_pct >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                {data.change_pct >= 0 ? '+' : ''}{data.change_pct.toFixed(2)}% (1D)
              </div>
              <span className="text-[10px] text-slate-400 font-mono block">
                {data.is_live_data ? '🟢 Live Market Quote' : '📁 DB Cached Snapshot'}
              </span>
            </div>

            <div className="p-5 rounded-2xl bg-[#090d19] border border-white/[0.08] space-y-1">
              <span className="text-[10px] font-mono text-slate-400 uppercase">52-Week Range & Position</span>
              <div className="text-sm font-mono text-slate-300 font-semibold">
                ₹{data.low_52w.toLocaleString('en-IN')} — ₹{data.high_52w.toLocaleString('en-IN')}
              </div>
              <div className="w-full bg-white/[0.05] h-1.5 rounded-full overflow-hidden mt-2">
                <div
                  className="bg-amber-400 h-full rounded-full"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(
                        0,
                        ((data.current_price - data.low_52w) / Math.max(1, data.high_52w - data.low_52w)) * 100
                      )
                    )}%`,
                  }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1">
                <span>52W Low: {data.technical_overview ? `${data.technical_overview.pct_from_52w_low > 0 ? '+' : ''}${data.technical_overview.pct_from_52w_low}%` : ''}</span>
                <span>52W High: {data.technical_overview ? `${data.technical_overview.pct_from_52w_high}%` : ''}</span>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-[#090d19] border border-white/[0.08] space-y-1">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Technical Trend Structure</span>
              <div className="text-xs font-mono font-bold text-slate-200">
                {data.technical_overview ? data.technical_overview.trend_phase.replace(/_/g, ' ') : 'NEUTRAL RANGE'}
              </div>
              <div className="text-xs font-mono text-slate-400">
                50-DMA: ₹{data.dma_50 > 0 ? data.dma_50.toLocaleString('en-IN') : 'N/A'} • 200-DMA: ₹{data.dma_200 > 0 ? data.dma_200.toLocaleString('en-IN') : 'N/A'}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] font-mono text-slate-400">
                  RSI(14): <strong className="text-slate-200">{data.technical_overview?.rsi_14.toFixed(1) || 50.0}</strong>
                </span>
                <span
                  className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full ${
                    data.technical_overview?.trend_phase === 'BULLISH_MARKUP'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : data.technical_overview?.trend_phase === 'PULLBACK_IN_UPTREND'
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                      : data.technical_overview?.trend_phase === 'BEARISH_MARKDOWN'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  }`}
                >
                  {data.technical_overview?.trend_phase === 'BULLISH_MARKUP' ? 'Strong Uptrend' : data.technical_overview?.trend_phase === 'PULLBACK_IN_UPTREND' ? 'Dip Opportunity' : 'Consolidation'}
                </span>
              </div>
            </div>
          </div>

          {/* Interactive Price Range & Key Levels Ladder */}
          <PriceRangeLadder
            currentPrice={data.current_price}
            low52w={data.low_52w}
            high52w={data.high_52w}
            dma50={data.dma_50}
            dma200={data.dma_200}
            dipTargetPrice={data.tactical_action?.dip_target_price}
          />

          {/* 4. HERO TACTICAL DECISION & EXECUTION PLAN */}
          <div className="p-6 rounded-3xl bg-gradient-to-br from-[#0c1224] via-[#090e1c] to-[#070b16] border border-white/[0.12] shadow-2xl space-y-6">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-white/[0.08]">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Institutional Decision Verdict</span>
                  <span className="text-xs font-mono text-amber-400">({data.matrix_quadrant})</span>
                </div>
                <div className="text-3xl font-black tracking-tight text-white flex items-center gap-3">
                  <span>{data.verdict_badge}</span>
                  <span
                    className={`text-xs px-3 py-1 rounded-full font-bold font-mono ${
                      data.is_investment_worthy
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                    }`}
                  >
                    {data.is_investment_worthy ? '✓ ALLOCATION WORTHY' : '✕ EXERCISE CAUTION'}
                  </span>
                </div>
              </div>

              {/* Overall Conviction Gauge */}
              <div className="flex items-center gap-4 bg-white/[0.02] p-3 rounded-2xl border border-white/[0.05]">
                <div className="text-right">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Investment Score</span>
                  <span className="text-xs font-mono font-bold text-amber-300">
                    {data.score_breakdowns?.investment_conviction.tier || 'Core Allocation'}
                  </span>
                </div>
                <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex flex-col items-center justify-center font-mono font-black text-2xl text-amber-400">
                  {data.investment_score.toFixed(0)}
                  <span className="text-[8px] font-normal text-slate-400">/ 100</span>
                </div>
              </div>
            </div>

            {/* Verdict Reasoning Callout */}
            <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] flex items-start gap-3">
              <Compass className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider block mb-1">
                  Tactical Reasoning & Action Mandate
                </span>
                <p className="text-xs leading-relaxed text-slate-300 font-sans font-medium">
                  {data.tactical_action?.verdict_reasoning || data.thesis_rationale}
                </p>
              </div>
            </div>

            {/* Tactical Execution Parameters Grid */}
            {data.tactical_action && (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05] space-y-1">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Recommended Entry Zone</span>
                  <div className="text-sm font-mono font-bold text-emerald-400">
                    {data.tactical_action.recommended_entry_min > 0
                      ? `₹${data.tactical_action.recommended_entry_min.toLocaleString('en-IN')} — ₹${data.tactical_action.recommended_entry_max.toLocaleString('en-IN')}`
                      : 'Sidelined (No Entry)'}
                  </div>
                  <span className="text-[9px] text-slate-400 font-mono block">Target accumulation band</span>
                </div>

                <div className="p-3.5 rounded-xl bg-amber-500/[0.04] border border-amber-500/20 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-amber-300 uppercase">Wait-for-Dip Target</span>
                    <span className="text-[9px] font-mono font-bold text-amber-400">
                      {data.tactical_action.dip_discount_pct}%
                    </span>
                  </div>
                  <div className="text-sm font-mono font-bold text-white">
                    ₹{data.tactical_action.dip_target_price.toLocaleString('en-IN')}
                  </div>
                  <span className="text-[9px] text-slate-400 font-mono block">Pullback to 50-DMA support</span>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05] space-y-1">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Stop-Loss Invalidation</span>
                  <div className="text-sm font-mono font-bold text-rose-400">
                    ₹{data.tactical_action.stop_loss_level.toLocaleString('en-IN')}
                  </div>
                  <span className="text-[9px] text-slate-400 font-mono block">Below structural 200-DMA</span>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05] space-y-1">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">12M Target (Base / Bull)</span>
                  <div className="text-sm font-mono font-bold text-sky-300">
                    ₹{data.tactical_action.target_price_12m.toLocaleString('en-IN')} / ₹{data.tactical_action.target_price_bull.toLocaleString('en-IN')}
                  </div>
                  <span className="text-[9px] text-slate-400 font-mono block">Fundamental scenario target</span>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05] space-y-1">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Downside / Upside Skew</span>
                  <div className="text-sm font-mono font-bold text-amber-300">
                    {data.tactical_action.risk_reward_ratio.toFixed(2)}x
                  </div>
                  <span className="text-[9px] text-slate-400 font-mono block">Favorable institutional ratio</span>
                </div>
              </div>
            )}

            {/* Tactical Wishlist & Target List Action Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-amber-500/[0.04] border border-amber-500/20">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
                  <BookmarkPlus className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
                    <span>Tactical Wishlist & Dip Accumulation</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30">
                      TARGET: ₹{data.tactical_action?.dip_target_price.toLocaleString('en-IN') || data.current_price.toLocaleString('en-IN')}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-0.5">
                    Save {data.symbol} to your dedicated Target List to monitor distance to pullback and planned capital deployment.
                  </p>
                </div>
              </div>
              <button
                onClick={handleOpenAddModal}
                className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-400 hover:brightness-110 text-slate-950 font-bold text-xs font-mono transition-all shadow-md shadow-amber-500/20 cursor-pointer whitespace-nowrap shrink-0"
              >
                <BookmarkPlus className="w-4 h-4" />
                <span>+ Add to Target List / Wishlist</span>
              </button>
            </div>
          </div>

          {/* 5. DECOUPLED FACTOR SCORES WITH DETAILED EXPLANATIONS */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Layers className="w-5 h-5 text-amber-400" />
                  Factor Pillar Scores & Diagnostic Meanings
                </h3>
                <p className="text-xs text-slate-400">
                  Click any factor pillar card to inspect underlying sub-metrics, rating tiers, and institutional interpretations.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
              {/* Radar Pentagon Profile Chart */}
              <div className="lg:col-span-4 glass-panel p-5 rounded-3xl flex flex-col items-center justify-between border border-white/[0.08] shadow-xl">
                <div className="w-full flex items-center justify-between pb-2 border-b border-white/[0.06]">
                  <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-sky-400 flex items-center">
                    <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-400" />
                    Factor Profile Star
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 font-bold">BASE 50</span>
                </div>
                <FactorRadarChart
                  size={250}
                  stockName={data.symbol}
                  data={[
                    { axis: 'Quality', score: data.business_quality_score, benchmark: 55, description: data.score_breakdowns?.business_quality?.tier },
                    { axis: 'Valuation', score: data.valuation_score, benchmark: 50, description: data.score_breakdowns?.valuation?.tier },
                    { axis: 'Growth', score: data.growth_score, benchmark: 52, description: data.score_breakdowns?.growth?.tier },
                    { axis: 'Low Risk', score: data.risk_score, benchmark: 60, description: data.score_breakdowns?.risk?.tier },
                    { axis: 'Technicals', score: data.technical_overview?.rsi_14 || 50, benchmark: 50, description: data.technical_overview?.trend_phase },
                    { axis: 'Conviction', score: data.investment_score, benchmark: 50, description: data.verdict_badge },
                  ]}
                />
                <div className="w-full text-center text-[10px] font-mono text-slate-400 pt-2 border-t border-white/[0.06]">
                  Composite Conviction: <strong className="text-white font-bold">{data.investment_score.toFixed(1)}/100</strong>
                </div>
              </div>

              {/* 4 Factor Pillars Grid */}
              <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Business Quality Score */}
                <div
                  onClick={() => setActiveScoreDetail(activeScoreDetail === 'bqs' ? null : 'bqs')}
                  className={`p-5 rounded-2xl bg-[#090d19] border transition-all cursor-pointer space-y-3 ${
                    activeScoreDetail === 'bqs' ? 'border-sky-400 ring-1 ring-sky-400/30 shadow-lg' : 'border-white/[0.08] hover:border-white/20'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[10px] font-mono text-slate-400 uppercase block">Business Quality (BQS)</span>
                      <span className="text-2xl font-black font-mono text-sky-400 block mt-1">
                        {data.business_quality_score.toFixed(1)}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-sky-500/10 text-sky-400 border border-sky-500/20 font-bold">
                      Moat & ROCE
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 font-medium">
                    {data.score_breakdowns?.business_quality.tier || 'Economic Moat'}
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    {data.score_breakdowns?.business_quality.interpretation || 'Evaluates competitive moat, pricing power, and return on capital.'}
                  </p>
                  <span className="text-[10px] text-sky-400 font-mono flex items-center gap-1">
                    <HelpCircle className="w-3 h-3" /> Click to view sub-metrics
                  </span>
                </div>

                {/* Valuation Score */}
                <div
                  onClick={() => setActiveScoreDetail(activeScoreDetail === 'val' ? null : 'val')}
                  className={`p-5 rounded-2xl bg-[#090d19] border transition-all cursor-pointer space-y-3 ${
                    activeScoreDetail === 'val' ? 'border-emerald-400 ring-1 ring-emerald-400/30 shadow-lg' : 'border-white/[0.08] hover:border-white/20'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[10px] font-mono text-slate-400 uppercase block">Valuation Score</span>
                      <span className="text-2xl font-black font-mono text-emerald-400 block mt-1">
                        {data.valuation_score.toFixed(1)}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                      Margin of Safety
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 font-medium">
                    {data.score_breakdowns?.valuation.tier || 'Fair Value'}
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    {data.score_breakdowns?.valuation.interpretation || 'Measures multiple safety and Reverse-DCF implied cash flow expectations.'}
                  </p>
                  <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                    <HelpCircle className="w-3 h-3" /> Click to view sub-metrics
                  </span>
                </div>

                {/* Growth Score */}
                <div
                  onClick={() => setActiveScoreDetail(activeScoreDetail === 'growth' ? null : 'growth')}
                  className={`p-5 rounded-2xl bg-[#090d19] border transition-all cursor-pointer space-y-3 ${
                    activeScoreDetail === 'growth' ? 'border-amber-400 ring-1 ring-amber-400/30 shadow-lg' : 'border-white/[0.08] hover:border-white/20'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[10px] font-mono text-slate-400 uppercase block">Growth Score</span>
                      <span className="text-2xl font-black font-mono text-amber-400 block mt-1">
                        {data.growth_score.toFixed(1)}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
                      CAGR & Accel
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 font-medium">
                    {data.score_breakdowns?.growth.tier || 'Earnings Trajectory'}
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    {data.score_breakdowns?.growth.interpretation || 'Measures historical revenue/PAT CAGR and incremental capital efficiency.'}
                  </p>
                  <span className="text-[10px] text-amber-400 font-mono flex items-center gap-1">
                    <HelpCircle className="w-3 h-3" /> Click to view sub-metrics
                  </span>
                </div>

                {/* Solvency & Risk Score */}
                <div
                  onClick={() => setActiveScoreDetail(activeScoreDetail === 'risk' ? null : 'risk')}
                  className={`p-5 rounded-2xl bg-[#090d19] border transition-all cursor-pointer space-y-3 ${
                    activeScoreDetail === 'risk' ? 'border-purple-400 ring-1 ring-purple-400/30 shadow-lg' : 'border-white/[0.08] hover:border-white/20'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[10px] font-mono text-slate-400 uppercase block">Solvency Risk Score</span>
                      <span className="text-2xl font-black font-mono text-purple-400 block mt-1">
                        {data.risk_score.toFixed(1)}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20 font-bold">
                      Balance Sheet
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 font-medium">
                    {data.score_breakdowns?.risk.tier || 'Fortress Health'}
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    {data.score_breakdowns?.risk.interpretation || 'Assesses debt leverage, Altman-Z insolvency defense, and promoter pledging.'}
                  </p>
                  <span className="text-[10px] text-purple-400 font-mono flex items-center gap-1">
                    <HelpCircle className="w-3 h-3" /> Click to view sub-metrics
                  </span>
                </div>
              </div>
            </div>

            {/* Sub-Metrics Drawer / Expander Card */}
            {activeScoreDetail && data.score_breakdowns && (
              <div className="p-5 rounded-2xl bg-[#080c16] border border-white/[0.1] space-y-3 animate-fadeIn">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-mono font-bold text-white uppercase flex items-center gap-2">
                    <Activity className="w-4 h-4 text-amber-400" />
                    Underlying Sub-Metric Diagnostic: {activeScoreDetail.toUpperCase()}
                  </div>
                  <button
                    onClick={() => setActiveScoreDetail(null)}
                    className="text-[10px] font-mono text-slate-400 hover:text-white"
                  >
                    ✕ Close
                  </button>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                  {Object.entries(
                    activeScoreDetail === 'bqs'
                      ? data.score_breakdowns.business_quality.sub_metrics
                      : activeScoreDetail === 'val'
                      ? data.score_breakdowns.valuation.sub_metrics
                      : activeScoreDetail === 'growth'
                      ? data.score_breakdowns.growth.sub_metrics
                      : data.score_breakdowns.risk.sub_metrics
                  ).map(([key, val]) => (
                    <div key={key} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                      <span className="text-[10px] font-mono text-slate-400 uppercase block">{key.replace(/_/g, ' ')}</span>
                      <span className="text-sm font-mono font-bold text-white block mt-0.5">{String(val)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 6. Safety Redlines Alert */}
          {data.redlines_triggered && data.redlines_triggered.length > 0 ? (
            <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/40 text-rose-300 space-y-2">
              <div className="flex items-center space-x-2 font-bold text-sm">
                <AlertTriangle className="w-5 h-5 text-rose-400" />
                <span>Critical Redlines Triggered ({data.redlines_triggered.length}):</span>
              </div>
              <ul className="list-disc list-inside text-xs space-y-1 font-mono text-rose-200">
                {data.redlines_triggered.map((r, idx) => (
                  <li key={idx}>{r}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="p-3.5 rounded-2xl bg-emerald-950/20 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2 font-mono">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Redline Safety Audit Passed: Zero promoter pledging, debt distress, or auditor qualification flags.</span>
            </div>
          )}

          {/* 7. Multi-Horizon Return Projections */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Target className="w-5 h-5 text-sky-400" />
                  Multi-Horizon Scenario Expected Returns
                </h3>
                <p className="text-xs text-slate-400">
                  Calibrated across corporate quarterly earnings, semi-annual guidance, annual re-ratings, and 3-year compounding.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { title: '3-Month Horizon', sub: 'Quarterly Earnings Cycle', item: data.horizon_3m },
                { title: '6-Month Horizon', sub: 'Mid-Year Guidance Execution', item: data.horizon_6m },
                { title: '12-Month Horizon', sub: 'Annual Institutional Scenario', item: data.horizon_12m },
                { title: '3-Year Horizon', sub: 'Secular Compounding Trajectory', item: data.horizon_3y },
              ].map((h, idx) => (
                <div
                  key={idx}
                  className="p-5 rounded-2xl bg-[#090d19] border border-white/[0.08] hover:border-white/20 transition-all space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-bold text-sm text-white">{h.title}</div>
                      <div className="text-[10px] text-slate-400">{h.sub}</div>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-white/[0.05] text-slate-300">
                      {h.item.months} Mos
                    </span>
                  </div>

                  <div className="pt-2 border-t border-white/[0.05]">
                    <span className="text-[10px] font-mono text-slate-400 uppercase">Expected Return</span>
                    <div
                      className={`text-2xl font-black font-mono ${
                        h.item.expected_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {h.item.expected_return_pct >= 0 ? '+' : ''}{h.item.expected_return_pct.toFixed(1)}%
                      {h.item.cagr_pct ? <span className="text-xs font-normal text-slate-400"> ({h.item.cagr_pct.toFixed(1)}% p.a.)</span> : ''}
                    </div>
                  </div>

                  <div className="space-y-1 text-xs font-mono pt-1">
                    <div className="flex justify-between text-rose-400">
                      <span>Bear Target:</span>
                      <span>₹{h.item.target_price_bear.toFixed(1)} ({h.item.return_bear_pct >= 0 ? '+' : ''}{h.item.return_bear_pct.toFixed(1)}%)</span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>Base Target:</span>
                      <span>₹{h.item.target_price_base.toFixed(1)} ({h.item.return_base_pct >= 0 ? '+' : ''}{h.item.return_base_pct.toFixed(1)}%)</span>
                    </div>
                    <div className="flex justify-between text-emerald-400">
                      <span>Bull Target:</span>
                      <span>₹{h.item.target_price_bull.toFixed(1)} ({h.item.return_bull_pct >= 0 ? '+' : ''}{h.item.return_bull_pct.toFixed(1)}%)</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-white/[0.05] flex justify-between items-center text-[10px] font-mono text-slate-400">
                    <span>Downside/Upside:</span>
                    <span className="text-amber-300 font-bold">{h.item.downside_to_upside_ratio.toFixed(2)}x</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 8. STRUCTURED INSTITUTIONAL RESEARCH REPORT & NEWS STREAM */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Structured Report */}
            <div className="lg:col-span-2 p-6 rounded-2xl bg-[#090d19] border border-white/[0.08] space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <FileText className="w-5 h-5 text-amber-400" />
                  <h3 className="font-bold text-white text-base">Institutional Equity Research Report</h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  PM BRIEFING
                </span>
              </div>

              {/* Research Tabs */}
              <div className="flex items-center gap-1.5 border-b border-white/[0.08] pb-3 overflow-x-auto no-scrollbar">
                {[
                  { id: 'exec', label: 'Executive Thesis' },
                  { id: 'moat', label: 'Competitive Moat' },
                  { id: 'val', label: 'Valuation & Reverse DCF' },
                  { id: 'tech', label: 'Trend & Structure' },
                  { id: 'tactical', label: 'Tactical Plan' },
                ].map((t) => {
                  const isActive = activeThesisTab === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setActiveThesisTab(t.id as any)}
                      className={`px-3.5 py-1.5 rounded-xl text-xs font-mono font-bold transition-all duration-200 whitespace-nowrap cursor-pointer ${
                        isActive
                          ? 'bg-gradient-to-r from-amber-500/25 to-yellow-500/20 text-amber-200 border border-amber-400/50 shadow-[0_0_15px_rgba(245,158,11,0.25)]'
                          : 'text-slate-400 hover:text-white hover:bg-white/[0.04] border border-transparent'
                      }`}
                    >
                      {t.label}
                    </button>
                  );
                })}
              </div>

              {/* Active Tab Content with Fade-In Animation */}
              <div
                key={activeThesisTab}
                className="animate-fade-in p-5 rounded-2xl bg-[#060810]/80 border border-white/[0.06] text-xs leading-relaxed text-slate-300 font-sans min-h-[140px] shadow-inner"
              >
                {activeThesisTab === 'exec' && (
                  <div className="space-y-2">
                    <div className="font-bold text-slate-200 text-sm">Portfolio Manager Summary</div>
                    <p>{data.research_report?.executive_summary || data.thesis_rationale}</p>
                  </div>
                )}
                {activeThesisTab === 'moat' && (
                  <div className="space-y-2">
                    <div className="font-bold text-slate-200 text-sm">Franchise Moat & Capital Allocation</div>
                    <p>{data.research_report?.fundamental_moat || 'Evaluates returns on capital, balance sheet leverage, and moat depth.'}</p>
                  </div>
                )}
                {activeThesisTab === 'val' && (
                  <div className="space-y-2">
                    <div className="font-bold text-slate-200 text-sm">Market Expectations & Multiple Analysis</div>
                    <p>{data.research_report?.valuation_expectations || 'Reverse-DCF and earnings yield expectations analysis.'}</p>
                  </div>
                )}
                {activeThesisTab === 'tech' && (
                  <div className="space-y-2">
                    <div className="font-bold text-slate-200 text-sm">Trend, Moving Averages & Momentum</div>
                    <p>{data.research_report?.technical_trend || 'Technical moving averages and trend alignment.'}</p>
                  </div>
                )}
                {activeThesisTab === 'tactical' && (
                  <div className="space-y-2">
                    <div className="font-bold text-slate-200 text-sm">Tactical Execution & Dip Parameters</div>
                    <p>{data.research_report?.tactical_action_plan || 'Actionable entry, dip target, and risk control parameters.'}</p>
                  </div>
                )}
              </div>

              {/* Growth Catalysts vs Primary Risks */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                {data.growth_drivers && data.growth_drivers.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/20 space-y-2">
                    <span className="text-[11px] font-mono font-bold text-emerald-400 uppercase flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Key Growth Catalysts:
                    </span>
                    <ul className="list-disc list-inside text-xs space-y-1 text-slate-300 font-sans">
                      {data.growth_drivers.map((d, idx) => (
                        <li key={idx}>{d}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.primary_risks && data.primary_risks.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/20 space-y-2">
                    <span className="text-[11px] font-mono font-bold text-rose-400 uppercase flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5" /> Critical Risk Factors:
                    </span>
                    <ul className="list-disc list-inside text-xs space-y-1 text-slate-300 font-sans">
                      {data.primary_risks.map((r, idx) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* News Feed */}
            <div className="p-6 rounded-2xl bg-[#090d19] border border-white/[0.08] space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Activity className="w-5 h-5 text-emerald-400" />
                  <h3 className="font-bold text-white text-base">Market News & Sentiment</h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.05] text-slate-300">
                  Sent: {data.sentiment_score >= 0 ? '+' : ''}{data.sentiment_score.toFixed(2)}
                </span>
              </div>

              {data.headlines && data.headlines.length > 0 ? (
                <div className="space-y-3">
                  {data.headlines.map((h, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] space-y-1">
                      <div className="text-xs text-slate-200 font-medium leading-snug">{h.headline}</div>
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                        <span>{h.source || 'News'}</span>
                        <span>{h.published_at || ''}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500 font-mono py-12 text-center">
                  No breaking headlines recorded for {data.symbol}.
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* 5. ADD TO TARGET LIST / PORTFOLIO MODAL */}
      {isAddModalOpen && data && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-lg rounded-3xl bg-[#090d19] border border-white/[0.12] p-6 shadow-2xl space-y-5 text-slate-100 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <BookmarkPlus className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    Add {data.symbol} to List
                  </h3>
                  <p className="text-xs text-slate-400">
                    Track in tactical dip list or add to active capital portfolio
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="p-1.5 rounded-xl hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {addModalError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{addModalError}</span>
              </div>
            )}

            <form onSubmit={handleConfirmAdd} className="space-y-4 font-sans text-xs">
              {/* Destination Mode Selector */}
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-2">
                  Destination Target
                </label>
                <div className="grid grid-cols-2 gap-2 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <button
                    type="button"
                    onClick={() => setIsCreatingNew(false)}
                    className={`py-1.5 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      !isCreatingNew
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Existing List / Portfolio
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsCreatingNew(true)}
                    className={`py-1.5 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      isCreatingNew
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    + Create New List
                  </button>
                </div>
              </div>

              {/* Destination Selector or Creation Inputs */}
              {!isCreatingNew ? (
                <div>
                  <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Select Target List or Portfolio
                  </label>
                  <select
                    value={selectedDestId}
                    onChange={(e) => setSelectedDestId(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white font-medium focus:outline-none focus:border-amber-400 transition-colors"
                  >
                    {portfolios.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.portfolio_type === 'TARGETLIST' ? 'Target List' : 'Portfolio'} • {p.holdings_count} items)
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className="space-y-3 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
                  <div>
                    <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                      New List Name *
                    </label>
                    <input
                      type="text"
                      value={newListName}
                      onChange={(e) => setNewListName(e.target.value)}
                      placeholder="e.g. High-Conviction Dip Watchlist"
                      className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-amber-400 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                      List Purpose / Type
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setNewListType('TARGETLIST')}
                        className={`p-2 rounded-xl border text-left transition-all cursor-pointer ${
                          newListType === 'TARGETLIST'
                            ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                            : 'bg-white/[0.02] border-white/[0.06] text-slate-400'
                        }`}
                      >
                        <div className="font-bold text-[11px]">🎯 Target List</div>
                        <div className="text-[9px] text-slate-400 mt-0.5">Watchlist for dip triggers</div>
                      </button>
                      <button
                        type="button"
                        onClick={() => setNewListType('PORTFOLIO')}
                        className={`p-2 rounded-xl border text-left transition-all cursor-pointer ${
                          newListType === 'PORTFOLIO'
                            ? 'bg-sky-500/10 border-sky-500/40 text-sky-300'
                            : 'bg-white/[0.02] border-white/[0.06] text-slate-400'
                        }`}
                      >
                        <div className="font-bold text-[11px]">💼 Live Portfolio</div>
                        <div className="text-[9px] text-slate-400 mt-0.5">Capital & P&L tracking</div>
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                      Description (Optional)
                    </label>
                    <input
                      type="text"
                      value={newListDescription}
                      onChange={(e) => setNewListDescription(e.target.value)}
                      placeholder="e.g. Core compounders to buy at 50-DMA"
                      className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-amber-400 transition-colors"
                    />
                  </div>
                </div>
              )}

              {/* Shares & Price Section */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Planned Shares / Qty
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={addShares}
                    onChange={(e) => setAddShares(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white font-mono focus:outline-none focus:border-amber-400 transition-colors"
                  />
                  <div className="flex gap-1.5 mt-1.5">
                    {['10', '25', '50', '100'].map((qty) => (
                      <button
                        key={qty}
                        type="button"
                        onClick={() => setAddShares(qty)}
                        className="px-2 py-0.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] text-[10px] font-mono text-slate-400 hover:text-white transition-colors cursor-pointer"
                      >
                        {qty}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Target / Buy Price (₹)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={addPrice}
                    onChange={(e) => setAddPrice(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white font-mono focus:outline-none focus:border-amber-400 transition-colors"
                  />
                  <div className="text-[10px] font-mono text-slate-400 mt-1.5">
                    Est. Value: ₹{((parseFloat(addShares) || 0) * (parseFloat(addPrice) || 0)).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </div>
                </div>
              </div>

              {/* Quick Preset Buttons for Price */}
              <div>
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1.5">
                  1-Click Price Presets:
                </span>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setAddPrice(data.current_price.toFixed(1))}
                    className="px-2.5 py-1 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-[11px] font-mono text-slate-300 hover:text-white transition-colors cursor-pointer flex items-center gap-1.5"
                  >
                    <span>Live CMP:</span>
                    <strong className="text-white">₹{data.current_price.toFixed(1)}</strong>
                  </button>

                  {data.tactical_action?.dip_target_price && data.tactical_action.dip_target_price > 0 && (
                    <button
                      type="button"
                      onClick={() => setAddPrice(data.tactical_action!.dip_target_price.toFixed(1))}
                      className="px-2.5 py-1 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-[11px] font-mono text-amber-300 transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      <Target className="w-3 h-3 text-amber-400" />
                      <span>Dip Target:</span>
                      <strong className="text-white">₹{data.tactical_action.dip_target_price.toFixed(1)}</strong>
                      <span className="text-[9px] text-amber-400">(-{data.tactical_action.dip_discount_pct}%)</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Notes / Thesis */}
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  Tactical Notes & Conviction Thesis
                </label>
                <textarea
                  rows={3}
                  value={addNotes}
                  onChange={(e) => setAddNotes(e.target.value)}
                  placeholder="Record your entry trigger or thesis..."
                  className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-amber-400 transition-colors font-sans"
                />
              </div>

              {/* Modal Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  disabled={isSubmittingAdd}
                  className="px-4 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold text-slate-300 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingAdd}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-400 hover:brightness-110 text-slate-950 font-bold text-xs font-mono transition-all shadow-lg shadow-amber-500/20 cursor-pointer disabled:opacity-50"
                >
                  <BookmarkPlus className="w-4 h-4" />
                  <span>{isSubmittingAdd ? 'Saving...' : 'Confirm & Save'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 6. TOAST NOTIFICATION */}
      {toastNotification && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 p-4 rounded-2xl bg-[#0c1224] border border-amber-500/40 shadow-2xl animate-slideUp text-xs font-sans">
          <div className="p-1.5 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <div className="space-y-0.5">
            <div className="text-white font-medium">{toastNotification.message}</div>
            {onNavigateTab && (
              <button
                onClick={() => {
                  setToastNotification(null);
                  onNavigateTab('targetlist');
                }}
                className="text-amber-400 hover:text-amber-300 font-mono text-[11px] font-bold flex items-center gap-1 hover:underline cursor-pointer"
              >
                <span>View in Target Lists</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            )}
          </div>
          <button
            onClick={() => setToastNotification(null)}
            className="p-1 rounded-lg hover:bg-white/[0.08] text-slate-400 hover:text-white transition-colors cursor-pointer ml-2"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
