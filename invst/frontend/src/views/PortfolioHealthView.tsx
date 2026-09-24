import React, { useState, useEffect, useRef } from 'react';
import {
  Briefcase,
  Plus,
  Trash2,
  Upload,
  AlertTriangle,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2,
  Sparkles,
  ShieldAlert,
  PieChart,
  Activity,
  Calendar,
  ChevronDown,
  ChevronUp,
  Coins,
  Target,
  Compass,
  RefreshCw,
  FolderPlus,
  BookmarkPlus,
  X,
  AlertCircle,
} from 'lucide-react';
import {
  fetchPortfolioHoldings,
  savePortfolioHoldings,
  evaluatePortfolioHealth,
  fetchPortfolios,
  fetchPortfolio,
  createPortfolio,
  deletePortfolio,
} from '../api/client';
import {
  UserHoldingItem,
  PortfolioHealthResponse,
  PortfolioSummary,
  PortfolioDetail,
} from '../types/api';

export const PortfolioHealthView: React.FC = () => {
  // Multi-Portfolio & Target List state
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>('default');
  const [activePortfolioDetail, setActivePortfolioDetail] = useState<PortfolioDetail | null>(null);

  // Create Portfolio Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [holdings, setHoldings] = useState<UserHoldingItem[]>([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [newShares, setNewShares] = useState('');
  const [newPrice, setNewPrice] = useState('');
  const [newTargetPrice, setNewTargetPrice] = useState('');
  const [newNotes, setNewNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [report, setReport] = useState<PortfolioHealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const [filterAction, setFilterAction] = useState<string>('ALL');

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadPortfolios();
  }, []);

  const loadPortfolios = async (targetId?: string) => {
    try {
      const all = await fetchPortfolios('PORTFOLIO');
      // Show ONLY live investment portfolios in My Portfolio view (Target Lists are in dedicated section)
      const liveOnly = all.filter((p) => p.portfolio_type === 'PORTFOLIO');
      setPortfolios(liveOnly);
      const activeId =
        targetId ||
        (liveOnly.some((p) => p.id === selectedPortfolioId) ? selectedPortfolioId : (liveOnly[0]?.id || 'default'));
      setSelectedPortfolioId(activeId);
      await loadSpecificPortfolio(activeId);
    } catch {
      await loadSavedHoldings();
    }
  };

  const loadSpecificPortfolio = async (portId: string) => {
    try {
      const detail = await fetchPortfolio(portId);
      setActivePortfolioDetail(detail);
      const hList = detail?.holdings || [];
      setHoldings(hList);
      if (hList.length > 0) {
        await runDiagnosis(hList);
      } else {
        setReport(null);
      }
    } catch {
      await loadSavedHoldings();
    }
  };

  const handleSelectPortfolio = async (id: string) => {
    setSelectedPortfolioId(id);
    await loadSpecificPortfolio(id);
  };

  const handleCreatePortfolio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createName.trim()) {
      setCreateError('Please enter a name for the portfolio.');
      return;
    }
    setIsCreating(true);
    setCreateError(null);
    try {
      const created = await createPortfolio({
        name: createName.trim(),
        description: createDesc.trim() || undefined,
        portfolio_type: 'PORTFOLIO',
      });
      setIsCreateModalOpen(false);
      setCreateName('');
      setCreateDesc('');
      await loadPortfolios(created.id);
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create portfolio.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeletePortfolio = async () => {
    if (selectedPortfolioId === 'default') {
      alert('The Main Portfolio cannot be deleted.');
      return;
    }
    if (
      !window.confirm(
        `Are you sure you want to delete portfolio "${activePortfolioDetail?.name || selectedPortfolioId}"?`,
      )
    ) {
      return;
    }
    try {
      await deletePortfolio(selectedPortfolioId);
      await loadPortfolios('default');
    } catch (err: any) {
      setError(err.message || 'Failed to delete portfolio.');
    }
  };

  const loadSavedHoldings = async () => {
    try {
      const saved = await fetchPortfolioHoldings();
      if (saved && saved.length > 0) {
        setHoldings(saved);
        await runDiagnosis(saved);
      } else {
        setHoldings([]);
        setReport(null);
      }
    } catch {
      setHoldings([]);
      setReport(null);
    }
  };

  const handleLoadDemoHoldings = () => {
    const demo: UserHoldingItem[] = [
      { symbol: 'TCS', shares: 15, buy_price: 1380 },
      { symbol: 'INFY', shares: 20, buy_price: 1850 },
      { symbol: 'HDFCBANK', shares: 25, buy_price: 1250 },
      { symbol: 'RELIANCE', shares: 10, buy_price: 2200 },
      { symbol: 'NIFTYBEES', shares: 100, buy_price: 260 },
    ];
    setHoldings(demo);
    runDiagnosis(demo);
  };

  const runDiagnosis = async (currentHoldings: UserHoldingItem[]) => {
    if (!currentHoldings || currentHoldings.length === 0) {
      setReport(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await evaluatePortfolioHealth(currentHoldings);
      setReport(res);
    } catch (err: any) {
      setError(err.message || 'Failed to diagnose portfolio health.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddPosition = async (e: React.FormEvent) => {
    e.preventDefault();
    const sym = newSymbol.trim().toUpperCase();
    const sh = parseFloat(newShares);
    const pr = parseFloat(newPrice);
    const tp = newTargetPrice ? parseFloat(newTargetPrice) : undefined;

    if (!sym || isNaN(sh) || sh <= 0 || isNaN(pr) || pr <= 0) {
      setError('Please provide a valid Symbol, Shares (>0), and Buy Price (>0).');
      return;
    }

    const newHolding: UserHoldingItem = {
      symbol: sym,
      shares: sh,
      buy_price: pr,
      target_price: tp && !isNaN(tp) ? tp : undefined,
      notes: newNotes.trim() || undefined,
    };

    const updated = [...holdings.filter((h) => h.symbol !== sym), newHolding];
    setHoldings(updated);
    setNewSymbol('');
    setNewShares('');
    setNewPrice('');
    setNewTargetPrice('');
    setNewNotes('');
    setError(null);
    runDiagnosis(updated);
    try {
      await savePortfolioHoldings(updated, selectedPortfolioId);
      const list = await fetchPortfolios('PORTFOLIO');
      setPortfolios(list.filter((p) => p.portfolio_type === 'PORTFOLIO'));
    } catch {}
  };

  const handleRemovePosition = async (sym: string) => {
    const updated = holdings.filter((h) => h.symbol !== sym);
    setHoldings(updated);
    runDiagnosis(updated);
    try {
      await savePortfolioHoldings(updated, selectedPortfolioId);
      const list = await fetchPortfolios('PORTFOLIO');
      setPortfolios(list.filter((p) => p.portfolio_type === 'PORTFOLIO'));
    } catch {}
  };

  const handleQuickAddReplacement = async (sym: string) => {
    if (holdings.some((h) => h.symbol === sym)) return;
    const updated = [...holdings, { symbol: sym, shares: 10, buy_price: 1000 }];
    setHoldings(updated);
    runDiagnosis(updated);
    try {
      await savePortfolioHoldings(updated, selectedPortfolioId);
      const list = await fetchPortfolios('PORTFOLIO');
      setPortfolios(list.filter((p) => p.portfolio_type === 'PORTFOLIO'));
    } catch {}
  };

  const handleSaveHoldings = async () => {
    setSaving(true);
    try {
      await savePortfolioHoldings(holdings, selectedPortfolioId);
      await runDiagnosis(holdings);
      const list = await fetchPortfolios('PORTFOLIO');
      setPortfolios(list.filter((p) => p.portfolio_type === 'PORTFOLIO'));
    } catch (err: any) {
      setError(err.message || 'Failed to save holdings.');
    } finally {
      setSaving(false);
    }
  };

  const handleCsvUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string;
        const lines = text.split('\n');
        if (lines.length < 2) return;

        const header = lines[0].split(',').map((h) => h.trim().toLowerCase());
        const symIdx = header.findIndex((h) => h.includes('symbol') || h.includes('ticker') || h.includes('stock'));
        const shIdx = header.findIndex((h) => h.includes('share') || h.includes('qty') || h.includes('quantity'));
        const prIdx = header.findIndex((h) => h.includes('buy') || h.includes('price') || h.includes('avg') || h.includes('cost'));
        const tpIdx = header.findIndex((h) => h.includes('target'));
        const noteIdx = header.findIndex((h) => h.includes('note') || h.includes('thesis'));

        if (symIdx === -1 || shIdx === -1 || prIdx === -1) {
          setError('CSV must contain headers for Symbol, Shares/Quantity, and Buy Price.');
          return;
        }

        const parsed: UserHoldingItem[] = [];
        for (let i = 1; i < lines.length; i++) {
          const row = lines[i].split(',').map((cell) => cell.trim());
          if (row.length <= Math.max(symIdx, shIdx, prIdx)) continue;
          const s = row[symIdx]?.toUpperCase();
          const sh = parseFloat(row[shIdx]);
          const pr = parseFloat(row[prIdx]);
          const tp = tpIdx !== -1 && row[tpIdx] ? parseFloat(row[tpIdx]) : undefined;
          const nt = noteIdx !== -1 && row[noteIdx] ? row[noteIdx] : undefined;
          if (s && !isNaN(sh) && sh > 0 && !isNaN(pr) && pr > 0) {
            parsed.push({
              symbol: s,
              shares: sh,
              buy_price: pr,
              target_price: tp && !isNaN(tp) ? tp : undefined,
              notes: nt,
            });
          }
        }

        if (parsed.length > 0) {
          setHoldings(parsed);
          setError(null);
          runDiagnosis(parsed);
          await savePortfolioHoldings(parsed, selectedPortfolioId);
          const list = await fetchPortfolios('PORTFOLIO');
          setPortfolios(list.filter((p) => p.portfolio_type === 'PORTFOLIO'));
        } else {
          setError('No valid stock rows found in CSV.');
        }
      } catch (err: any) {
        setError('Error parsing CSV file: ' + err.message);
      }
    };
    reader.readAsText(file);
  };

  const filteredPositions = report?.positions.filter((p) => {
    if (filterAction === 'ALL') return true;
    return p.action_verdict === filterAction;
  }) || [];

  return (
    <div className="space-y-8 animate-fadeIn text-slate-100 pb-16">
      {/* 1. Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-3xl bg-gradient-to-r from-[#0d1222] via-[#090d19] to-[#0d1222] border border-white/[0.08] shadow-2xl">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              <Briefcase className="w-6 h-6 text-sky-400" />
              Portfolio Health & Tactical Rebalancer
            </h1>
            <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20 font-bold uppercase tracking-wider">
              INSTITUTIONAL GRADE
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time factor health audit • Multi-horizon wealth projections • Concrete share rebalancing & dip accumulation limits
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <input
            type="file"
            accept=".csv"
            ref={fileInputRef}
            onChange={handleCsvUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-semibold text-slate-200 transition-all cursor-pointer hover:border-white/[0.2]"
          >
            <Upload className="w-4 h-4 text-sky-400" />
            <span>Import CSV</span>
          </button>

          <button
            onClick={() => runDiagnosis(holdings)}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-semibold text-slate-200 transition-all cursor-pointer disabled:opacity-50"
            title="Re-run health diagnosis"
          >
            <RefreshCw className={`w-4 h-4 text-amber-400 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleSaveHoldings}
            disabled={saving}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-winsor-600 to-sky-500 text-white text-xs font-bold shadow-lg shadow-winsor-600/30 hover:brightness-110 transition-all cursor-pointer disabled:opacity-50"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Holdings'}</span>
          </button>
        </div>
      </div>

      {/* 2. Portfolio Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-3xl bg-[#090d19] border border-white/[0.08] shadow-xl">
        <div className="flex items-center space-x-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5 px-2 shrink-0">
            <Briefcase className="w-4 h-4 text-sky-400" />
            <span>Portfolios:</span>
          </div>

          <div className="flex items-center gap-2 flex-nowrap">
            {portfolios.map((p) => {
              const isSelected = p.id === selectedPortfolioId;
              return (
                <button
                  key={p.id}
                  onClick={() => handleSelectPortfolio(p.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-2xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-lg shadow-sky-500/10'
                      : 'bg-white/[0.02] hover:bg-white/[0.05] text-slate-400 hover:text-slate-200 border border-white/[0.05]'
                  }`}
                >
                  <span className="text-sm">💼</span>
                  <span>{p.name}</span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                      isSelected
                        ? 'bg-sky-400/20 text-sky-200'
                        : 'bg-white/[0.06] text-slate-400'
                    }`}
                  >
                    {p.holdings_count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
          <button
            onClick={() => {
              setCreateError(null);
              setIsCreateModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-semibold text-slate-200 hover:text-white transition-colors cursor-pointer"
          >
            <FolderPlus className="w-4 h-4 text-sky-400" />
            <span>+ New Portfolio</span>
          </button>

          {selectedPortfolioId !== 'default' && (
            <button
              onClick={handleDeletePortfolio}
              className="flex items-center gap-1.5 px-3 py-2 rounded-2xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-xs font-semibold text-rose-300 transition-colors cursor-pointer"
              title="Delete this portfolio"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="p-12 flex flex-col items-center justify-center space-y-3">
          <div className="w-9 h-9 border-2 border-sky-500/20 border-t-sky-400 rounded-full animate-spin" />
          <p className="text-xs font-mono text-slate-400">Diagnosing portfolio factor health, scenario horizons, and concentration...</p>
        </div>
      )}

      {/* 2. Top KPI Scorecards Bento */}
      {report && !loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-1 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-sky-500/5 rounded-full blur-2xl pointer-events-none" />
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Coins className="w-3.5 h-3.5 text-sky-400" />
              Portfolio Market Value
            </span>
            <div className="text-2xl font-black text-white tracking-tight">
              ₹{report.total_current_value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Cost Basis: ₹{report.total_invested.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
          </div>

          <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-1 shadow-lg relative overflow-hidden">
            <div className={`absolute top-0 right-0 w-24 h-24 ${report.total_unrealized_pnl >= 0 ? 'bg-emerald-500/5' : 'bg-rose-500/5'} rounded-full blur-2xl pointer-events-none`} />
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              Total Unrealized P&L
            </span>
            <div
              className={`text-2xl font-black font-mono flex items-center gap-1 tracking-tight ${
                report.total_unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {report.total_unrealized_pnl >= 0 ? <ArrowUpRight className="w-5 h-5" /> : <ArrowDownRight className="w-5 h-5" />}
              {report.total_unrealized_pnl >= 0 ? '+' : ''}₹{Math.abs(report.total_unrealized_pnl).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
            <div className={`text-xs font-mono font-bold ${report.total_unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {report.total_unrealized_pnl >= 0 ? '+' : ''}{report.total_unrealized_pnl_pct.toFixed(2)}% Net Return
            </div>
          </div>

          <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-1 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full blur-2xl pointer-events-none" />
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Portfolio Health Score
            </span>
            <div className="text-2xl font-black text-amber-400 font-mono tracking-tight">
              {report.overall_health_score.toFixed(1)} <span className="text-xs text-slate-500 font-normal">/ 100</span>
            </div>
            <div className="text-xs font-mono flex items-center gap-1.5">
              <span className="text-slate-400">Status:</span>
              <span
                className={`font-bold px-2 py-0.5 rounded text-[10px] ${
                  report.overall_health_grade === 'EXCELLENT'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : report.overall_health_grade === 'GOOD'
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                    : report.overall_health_grade === 'NEEDS_ATTENTION'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                }`}
              >
                {report.overall_health_grade.replace('_', ' ')}
              </span>
            </div>
          </div>

          <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-1 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-2xl pointer-events-none" />
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-purple-400" />
              Diversification Index (HHI)
            </span>
            <div className="text-2xl font-black text-white font-mono tracking-tight">
              {report.diversification?.hhi_score.toLocaleString() || 'N/A'}
            </div>
            <div className="text-xs text-slate-400 font-mono flex items-center gap-1.5">
              <span className="text-purple-300 font-semibold">
                {report.diversification?.diversification_tier.replace('_', ' ') || 'OPTIMAL'}
              </span>
              <span className="text-slate-500">•</span>
              <span>{report.diversification?.total_positions || report.positions.length} stocks</span>
            </div>
          </div>
        </div>
      )}

      {/* 3. Multi-Horizon Portfolio Aggregate Forecast Bento */}
      {report?.portfolio_horizons && Object.keys(report.portfolio_horizons).length > 0 && (
        <div className="p-6 rounded-3xl bg-[#090d19] border border-white/[0.08] shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.06] pb-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Calendar className="w-5 h-5 text-sky-400" />
                Multi-Horizon Portfolio Expected Returns & Wealth Trajectory
              </h2>
              <p className="text-xs text-slate-400">
                Calibrated across corporate earnings guidance, valuation mean-reversion, and 3-year compounding.
              </p>
            </div>
            <span className="text-[11px] font-mono px-3 py-1 rounded-full bg-white/[0.03] text-slate-300 border border-white/[0.06] self-start sm:self-auto">
              Capital-Weighted Aggregate
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
            {Object.entries(report.portfolio_horizons).map(([code, horizon]) => {
              const isPositive = horizon.expected_return_pct >= 0;
              return (
                <div
                  key={code}
                  className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:border-sky-500/30 transition-all space-y-3"
                >
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      {code.toUpperCase()} Horizon
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {code === '3m' ? 'Quarterly' : code === '6m' ? 'Semi-Annual' : code === '12m' ? '1-Year Target' : '3Y Compounding'}
                    </span>
                  </div>

                  <div>
                    <div className="text-[10px] text-slate-400 uppercase">Expected Return</div>
                    <div
                      className={`text-2xl font-black ${
                        isPositive ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {isPositive ? '+' : ''}{horizon.expected_return_pct.toFixed(1)}%
                    </div>
                  </div>

                  <div className="pt-2 border-t border-white/[0.04] space-y-1 text-xs">
                    <div className="flex justify-between items-center text-slate-400">
                      <span>Projected Value:</span>
                      <span className="text-white font-bold">
                        ₹{horizon.projected_portfolio_value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    {horizon.cagr_pct !== null && horizon.cagr_pct !== undefined && (
                      <div className="flex justify-between items-center text-slate-400">
                        <span>Implied 3Y CAGR:</span>
                        <span className="text-sky-400 font-bold">+{horizon.cagr_pct.toFixed(1)}% / yr</span>
                      </div>
                    )}
                    <div className="flex justify-between items-center text-[10px] text-slate-500 pt-1">
                      <span>Bear: {horizon.bear_return_pct >= 0 ? '+' : ''}{horizon.bear_return_pct.toFixed(1)}%</span>
                      <span>Bull: +{horizon.bull_return_pct.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. Factor Health Explanations & Institutional Tiers */}
      {report?.factor_health && Object.keys(report.factor_health).length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {report.factor_health.business_quality && (
            <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                  <Target className="w-4 h-4 text-emerald-400" />
                  Business Quality Moat
                </span>
                <span className="text-xs font-mono font-bold text-emerald-400">
                  {report.factor_health.business_quality.score.toFixed(1)}/100
                </span>
              </div>
              <div>
                <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                  {report.factor_health.business_quality.tier.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {report.factor_health.business_quality.interpretation}
              </p>
            </div>
          )}

          {report.factor_health.valuation && (
            <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                  <Coins className="w-4 h-4 text-sky-400" />
                  Margin of Safety (Valuation)
                </span>
                <span className="text-xs font-mono font-bold text-sky-400">
                  {report.factor_health.valuation.score.toFixed(1)}/100
                </span>
              </div>
              <div>
                <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">
                  {report.factor_health.valuation.tier.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {report.factor_health.valuation.interpretation}
              </p>
            </div>
          )}

          {report.factor_health.risk_solvency && (
            <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-purple-400" />
                  Solvency & Balance Sheet
                </span>
                <span className="text-xs font-mono font-bold text-purple-400">
                  {report.factor_health.risk_solvency.score.toFixed(1)}/100
                </span>
              </div>
              <div>
                <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                  {report.factor_health.risk_solvency.tier.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {report.factor_health.risk_solvency.interpretation}
              </p>
            </div>
          )}
        </div>
      )}

      {/* 5. Critical Redline & Sector Concentration Alerts */}
      {report?.critical_redline_alerts && report.critical_redline_alerts.length > 0 && (
        <div className="p-5 rounded-3xl bg-rose-950/40 border border-rose-500/40 text-rose-300 space-y-3 shadow-xl">
          <div className="flex items-center space-x-2 font-bold text-sm">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <span>Critical Governance or Insolvency Redlines Detected:</span>
          </div>
          <ul className="list-disc list-inside text-xs space-y-1.5 font-mono text-rose-200">
            {report.critical_redline_alerts.map((cra, idx) => (
              <li key={idx} className="leading-relaxed">{cra}</li>
            ))}
          </ul>
        </div>
      )}

      {report?.sector_warnings && report.sector_warnings.length > 0 && (
        <div className="p-5 rounded-3xl bg-amber-950/30 border border-amber-500/30 text-amber-300 space-y-2 text-xs font-mono shadow-lg">
          <div className="flex items-center space-x-2 font-bold text-sm">
            <PieChart className="w-5 h-5 text-amber-400 shrink-0" />
            <span>Sector Concentration Cap Warnings (Exceeding 35% Limit):</span>
          </div>
          {report.sector_warnings.map((sw, idx) => (
            <div key={idx} className="text-slate-300">• {sw}</div>
          ))}
        </div>
      )}

      {/* 6. Capital Rebalancing Blueprint */}
      {report?.rebalancing_blueprint && report.rebalancing_blueprint.orders.length > 0 && (
        <div className="p-6 rounded-3xl bg-[#090d19] border border-amber-500/30 space-y-4 shadow-xl relative overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.06] pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Coins className="w-5 h-5 text-amber-400" />
                  Tactical Capital Rebalancing Blueprint
                </h2>
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                    report.rebalancing_blueprint.rebalance_urgency === 'CRITICAL'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      : report.rebalancing_blueprint.rebalance_urgency === 'HIGH'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  }`}
                >
                  {report.rebalancing_blueprint.rebalance_urgency} URGENCY
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {report.rebalancing_blueprint.strategic_summary}
              </p>
            </div>

            <div className="flex items-center gap-3 font-mono text-xs self-start sm:self-auto">
              <div className="px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-400 block text-[10px]">Cash to Unlock:</span>
                <span className="font-bold text-emerald-400">
                  ₹{report.rebalancing_blueprint.total_capital_unlocked.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </span>
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-400 block text-[10px]">Cash to Deploy:</span>
                <span className="font-bold text-sky-400">
                  ₹{report.rebalancing_blueprint.total_capital_needed.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </span>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] text-slate-400 font-mono uppercase text-[10px]">
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Shares</th>
                  <th className="py-2.5 px-3">Ref Price</th>
                  <th className="py-2.5 px-3">Cash Impact</th>
                  <th className="py-2.5 px-3">Target Weight</th>
                  <th className="py-2.5 px-3">Execution Rationale</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] font-mono">
                {report.rebalancing_blueprint.orders.map((o, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-3 font-bold text-white">{o.symbol}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          o.action === 'SELL'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : o.action === 'TRIM'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        }`}
                      >
                        {o.action}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-200 font-semibold">{o.shares.toFixed(0)}</td>
                    <td className="py-3 px-3 text-slate-300">₹{o.estimated_price.toLocaleString('en-IN', { maximumFractionDigits: 1 })}</td>
                    <td
                      className={`py-3 px-3 font-bold ${
                        o.capital_impact >= 0 ? 'text-emerald-400' : 'text-sky-400'
                      }`}
                    >
                      {o.capital_impact >= 0 ? '+' : ''}₹{Math.abs(o.capital_impact).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                    <td className="py-3 px-3 text-slate-300">{o.target_weight_pct.toFixed(1)}%</td>
                    <td className="py-3 px-3 text-slate-400 text-[11px] font-sans max-w-sm">{o.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 7. Enhanced Positions Blotter */}
      {report?.positions && report.positions.length > 0 && (
        <div className="p-6 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                Position-by-Position Tactical Advisory
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Summary Action: <span className="text-slate-200 font-mono font-semibold">{report.summary_action_plan}</span>
              </p>
            </div>

            {/* Action Filter */}
            <div className="flex items-center gap-1.5 font-mono text-xs">
              {['ALL', 'BUY_MORE', 'HOLD', 'TRIM', 'EXIT_SELL'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilterAction(f)}
                  className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer text-[11px] font-semibold ${
                    filterAction === f
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                      : 'bg-white/[0.03] text-slate-400 hover:text-slate-200 border border-white/[0.06]'
                  }`}
                >
                  {f === 'BUY_MORE' ? 'BUY' : f === 'EXIT_SELL' ? 'SELL' : f}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] text-slate-400 font-mono uppercase text-[10px]">
                  <th className="py-3 px-3">Symbol</th>
                  <th className="py-3 px-3">Shares</th>
                  <th className="py-3 px-3">Avg Cost</th>
                  <th className="py-3 px-3">CMP / Price (₹)</th>
                  <th className="py-3 px-3">Market Value</th>
                  <th className="py-3 px-3">Weight (Target)</th>
                  <th className="py-3 px-3">P&L %</th>
                  <th className="py-3 px-3">Tactical Action</th>
                  <th className="py-3 px-3">Dip Buy Zone</th>
                  <th className="py-3 px-3">Stop Loss</th>
                  <th className="py-3 px-3 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] font-mono">
                {filteredPositions.map((p) => {
                  const pnlSign = p.unrealized_pnl >= 0 ? '+' : '';
                  const isExpanded = expandedSymbol === p.symbol;
                  return (
                    <React.Fragment key={p.symbol}>
                      <tr
                        onClick={() => setExpandedSymbol(isExpanded ? null : p.symbol)}
                        className="hover:bg-white/[0.03] transition-colors cursor-pointer"
                      >
                        <td className="py-3.5 px-3">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-white text-sm">{p.symbol}</span>
                            {p.is_etf && (
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                ETF
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-slate-500 font-sans block">{p.sector}</span>
                        </td>
                        <td className="py-3.5 px-3 text-slate-300 font-semibold">{p.shares.toFixed(0)}</td>
                        <td className="py-3.5 px-3 text-slate-400">₹{p.buy_price.toFixed(1)}</td>
                        <td className="py-3.5 px-3 text-white font-bold">₹{p.current_price.toFixed(1)}</td>
                        <td className="py-3.5 px-3 text-slate-200 font-bold">
                          ₹{p.current_value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        </td>
                        <td className="py-3.5 px-3">
                          <span className="text-white font-semibold">{p.weight_pct.toFixed(1)}%</span>
                          <span className="text-slate-500 text-[10px] block">
                            Target: {p.target_weight_pct.toFixed(1)}%
                          </span>
                        </td>
                        <td className={`py-3.5 px-3 font-bold ${p.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {pnlSign}{p.unrealized_pnl_pct.toFixed(1)}%
                        </td>
                        <td className="py-3.5 px-3 whitespace-nowrap">
                          <span
                            className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                              p.action_verdict === 'BUY_MORE'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : p.action_verdict === 'TRIM'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : p.action_verdict === 'EXIT_SELL'
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                : 'bg-white/[0.05] text-slate-300 border border-white/[0.1]'
                            }`}
                          >
                            {p.action_badge}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 text-slate-300">
                          {p.dip_target_price > 0 ? (
                            <div>
                              <span>₹{p.dip_target_price.toFixed(1)}</span>
                              <span className="text-[10px] text-amber-400 block">(-{p.dip_discount_pct.toFixed(1)}%)</span>
                            </div>
                          ) : (
                            'N/A'
                          )}
                        </td>
                        <td className="py-3.5 px-3 text-rose-400 font-semibold">
                          ₹{p.stop_loss_level > 0 ? p.stop_loss_level.toFixed(1) : 'N/A'}
                        </td>
                        <td className="py-3.5 px-3 text-right">
                          <button className="p-1 rounded-lg text-slate-400 hover:text-white">
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </td>
                      </tr>

                      {/* Expanded Deep Diagnostic Drawer */}
                      {isExpanded && (
                        <tr className="bg-white/[0.015]">
                          <td colSpan={11} className="p-4 border-b border-white/[0.06]">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-sans text-xs">
                              <div className="space-y-1.5 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                                  Action Rationale & Share Adjustment
                                </span>
                                <p className="text-slate-200 leading-relaxed">{p.action_rationale}</p>
                                {p.shares_to_adjust !== 0 && (
                                  <div className="mt-2 pt-2 border-t border-white/[0.04] font-mono text-xs flex justify-between">
                                    <span className="text-slate-400">Share Delta:</span>
                                    <span className={p.shares_to_adjust > 0 ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}>
                                      {p.shares_to_adjust > 0 ? `+${p.shares_to_adjust.toFixed(0)} shares` : `${p.shares_to_adjust.toFixed(0)} shares`}
                                    </span>
                                  </div>
                                )}
                              </div>

                              <div className="space-y-1.5 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] font-mono">
                                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                                  Quality Moat & Technical Trend
                                </span>
                                <div className="text-slate-200">
                                  Quality Score: <span className="text-amber-400 font-bold">{p.business_quality_score.toFixed(1)}/100</span>
                                </div>
                                <div className="text-slate-300 text-[11px]">
                                  Tier: <span className="text-sky-300">{p.quality_tier.replace(/_/g, ' ')}</span>
                                </div>
                                <div className="text-slate-400 text-[11px]">
                                  Trend: <span className="text-slate-200">{p.technical_trend}</span>
                                </div>
                              </div>

                              <div className="space-y-1.5 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] font-mono">
                                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">
                                  Horizon Outlook & Risk Boundary
                                </span>
                                <div className="text-slate-200">
                                  12M Forecast: <span className="text-sky-400 font-bold">{p.expected_return_12m >= 0 ? '+' : ''}{p.expected_return_12m.toFixed(1)}%</span>
                                </div>
                                <div className="text-slate-300 text-[11px]">
                                  Hard Invalidation: ₹{p.stop_loss_level.toFixed(1)}
                                </div>
                                {p.redlines_triggered.length > 0 && (
                                  <div className="text-rose-400 text-[11px] font-bold">
                                    Redlines: {p.redlines_triggered.join(', ')}
                                  </div>
                                )}
                              </div>

                              {(p.notes || (p.target_price && p.target_price > 0)) && (
                                <div className="md:col-span-3 p-3 rounded-xl bg-amber-500/[0.04] border border-amber-500/20 font-sans text-xs flex items-start gap-2.5">
                                  <BookmarkPlus className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                                  <div className="space-y-0.5">
                                    <div className="font-mono font-bold text-amber-300 text-[11px] uppercase tracking-wider flex items-center gap-2">
                                      <span>Target Price & Tactical Notes</span>
                                      {p.target_price && p.target_price > 0 && (
                                        <span className="text-white bg-white/[0.06] px-2 py-0.5 rounded font-mono font-semibold">
                                          Target: ₹{p.target_price.toFixed(1)}
                                        </span>
                                      )}
                                    </div>
                                    {p.notes && <p className="text-slate-300 text-xs leading-relaxed">{p.notes}</p>}
                                  </div>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 8. Portfolio Holdings Manager (Add Position & Active Roster) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Add Position Card */}
        <div className="p-6 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-4 shadow-xl">
          <h3 className="font-bold text-white text-base flex items-center gap-2">
            <Plus className="w-5 h-5 text-amber-400" />
            Add Stock / ETF Holding
          </h3>
          <form onSubmit={handleAddPosition} className="space-y-3">
            <div>
              <label className="text-[10px] font-mono text-slate-400 uppercase block mb-1">Ticker Symbol (NSE)</label>
              <input
                type="text"
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                placeholder="e.g. TCS, RELIANCE, NIFTYBEES"
                className="w-full px-3 py-2 bg-[#060810] border border-white/[0.1] rounded-xl text-xs text-white font-mono uppercase focus:outline-none focus:border-amber-400 transition-colors"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase block mb-1">Shares</label>
                <input
                  type="number"
                  step="any"
                  value={newShares}
                  onChange={(e) => setNewShares(e.target.value)}
                  placeholder="e.g. 15"
                  className="w-full px-3 py-2 bg-[#060810] border border-white/[0.1] rounded-xl text-xs text-white font-mono focus:outline-none focus:border-amber-400 transition-colors"
                />
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase block mb-1">Buy / Cost Price (₹)</label>
                <input
                  type="number"
                  step="any"
                  value={newPrice}
                  onChange={(e) => setNewPrice(e.target.value)}
                  placeholder="e.g. 1450"
                  className="w-full px-3 py-2 bg-[#060810] border border-white/[0.1] rounded-xl text-xs text-white font-mono focus:outline-none focus:border-amber-400 transition-colors"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase block mb-1">Target Price (₹, Opt)</label>
                <input
                  type="number"
                  step="any"
                  value={newTargetPrice}
                  onChange={(e) => setNewTargetPrice(e.target.value)}
                  placeholder="e.g. 1320"
                  className="w-full px-3 py-2 bg-[#060810] border border-white/[0.1] rounded-xl text-xs text-white font-mono focus:outline-none focus:border-amber-400 transition-colors"
                />
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase block mb-1">Tactical Notes (Opt)</label>
                <input
                  type="text"
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="e.g. Buy at 50-DMA"
                  className="w-full px-3 py-2 bg-[#060810] border border-white/[0.1] rounded-xl text-xs text-white focus:outline-none focus:border-amber-400 transition-colors font-sans"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-400 text-slate-950 font-bold text-xs hover:brightness-110 transition-all cursor-pointer shadow-lg shadow-amber-500/20"
            >
              {activePortfolioDetail?.portfolio_type === 'TARGETLIST' ? 'Add to Target List' : 'Add to Portfolio'}
            </button>
          </form>
        </div>

        {/* Active Holding Roster with Quick Delete */}
        <div className="lg:col-span-2 p-6 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div>
              <h3 className="font-bold text-white text-base">
                {activePortfolioDetail?.name || 'Active Holding Roster'}
              </h3>
              <p className="text-xs text-slate-400">
                {activePortfolioDetail?.description || 'Manage, edit, and curate your active positions.'}
              </p>
            </div>
            <span className="text-xs font-mono text-slate-400 px-3 py-1 rounded-full bg-white/[0.04]">
              {holdings.length} {activePortfolioDetail?.portfolio_type === 'TARGETLIST' ? 'targets' : 'holdings'} recorded
            </span>
          </div>

          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {holdings.length === 0 ? (
              <div className="py-8 text-center space-y-3">
                <p className="text-slate-400 text-xs font-mono">
                  No active holdings recorded yet for this portfolio.
                </p>
                <button
                  type="button"
                  onClick={handleLoadDemoHoldings}
                  className="px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs text-amber-400 font-mono transition-colors cursor-pointer"
                >
                  📥 Load Demo Compounders
                </button>
              </div>
            ) : (
              holdings.map((h) => (
                <div
                  key={h.symbol}
                  className="flex items-center justify-between p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:border-white/[0.08] text-xs font-mono transition-all"
                >
                  <div className="flex flex-col space-y-1">
                    <div className="flex items-center space-x-3">
                      <span className="font-bold text-white text-sm">{h.symbol}</span>
                      <span className="text-slate-400">Qty: {h.shares}</span>
                      <span className="text-slate-400">@ ₹{h.buy_price.toFixed(1)}</span>
                      {h.target_price && h.target_price > 0 && (
                        <span className="text-amber-400 text-[11px] font-semibold">
                          Target: ₹{h.target_price.toFixed(1)}
                        </span>
                      )}
                      <span className="text-slate-500 text-[10px]">
                        (Cost: ₹{(h.shares * h.buy_price).toLocaleString('en-IN', { maximumFractionDigits: 0 })})
                      </span>
                    </div>
                    {h.notes && (
                      <span className="text-[11px] text-slate-400 font-sans truncate max-w-md">
                        {h.notes}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => handleRemovePosition(h.symbol)}
                    className="p-1.5 rounded-lg hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-all cursor-pointer shrink-0"
                    title="Remove position"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* 9. Suggested Reinvestments / High Conviction Alpha */}
      {report?.suggested_replacements && report.suggested_replacements.length > 0 && (
        <div className="p-6 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.06] pb-3">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-emerald-400" />
                Suggested High-Conviction Reinvestments
              </h3>
              <p className="text-xs text-slate-400">
                Top Arth IQ compounders to absorb freed-up cash from trims/exits or deploy fresh liquidity:
              </p>
            </div>
            <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20 self-start sm:self-auto">
              Top Ranked Moat & Margin
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono">
            {report.suggested_replacements.map((r) => (
              <div
                key={r.symbol}
                className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:border-emerald-500/30 transition-all space-y-2 flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-base font-black text-white">{r.symbol}</span>
                    <span className="text-[10px] text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded-full border border-sky-500/20">
                      {r.sector}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400">
                    Composite Score: <span className="font-bold text-amber-400">{r.composite_score.toFixed(1)}/100</span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-sans">{r.suggested_role}</div>
                </div>

                <button
                  onClick={() => handleQuickAddReplacement(r.symbol)}
                  className="w-full mt-2 py-1.5 rounded-xl bg-white/[0.04] hover:bg-emerald-500/20 border border-white/[0.08] hover:border-emerald-500/30 text-xs font-semibold text-emerald-300 transition-all cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add to Portfolio</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 10. CREATE NEW PORTFOLIO / TARGET LIST MODAL */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-md rounded-3xl bg-[#090d19] border border-white/[0.12] p-6 shadow-2xl space-y-5 text-slate-100">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <FolderPlus className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Create New Portfolio</h3>
                  <p className="text-xs text-slate-400">Set up a dedicated portfolio to track invested capital, holdings, and health</p>
                </div>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="p-1.5 rounded-xl hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {createError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreatePortfolio} className="space-y-4 font-sans text-xs">
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  Portfolio Name *
                </label>
                <input
                  type="text"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="e.g. Core Long-Term, High Beta Growth, Dividend Engine"
                  className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-sky-400 transition-colors"
                />
              </div>

              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  Description (Optional)
                </label>
                <input
                  type="text"
                  value={createDesc}
                  onChange={(e) => setCreateDesc(e.target.value)}
                  placeholder="e.g. Long-term blue chips, defensive moat holdings"
                  className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-sky-400 transition-colors"
                />
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  disabled={isCreating}
                  className="px-4 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold text-slate-300 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:brightness-110 text-white font-bold text-xs font-mono transition-all shadow-lg shadow-sky-500/20 cursor-pointer disabled:opacity-50"
                >
                  <FolderPlus className="w-4 h-4" />
                  <span>{isCreating ? 'Creating...' : 'Create Portfolio'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
