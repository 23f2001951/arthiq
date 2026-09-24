import React, { useState, useEffect, useRef } from 'react';
import {
  Target,
  Plus,
  Trash2,
  Upload,
  AlertTriangle,
  RefreshCw,
  Layers,
  FolderPlus,
  BookmarkPlus,
  X,
  AlertCircle,
  Search,
  SlidersHorizontal,
  Coins,
  Activity,
  Check,
  Briefcase,
} from 'lucide-react';
import {
  fetchPortfolios,
  fetchPortfolio,
  createPortfolio,
  deletePortfolio,
  savePortfolioHoldings,
  evaluatePortfolioHealth,
  moveStockBetweenPortfolios,
  addStockToPortfolio,
  analyzeStock,
} from '../api/client';
import {
  UserHoldingItem,
  PortfolioSummary,
  PortfolioDetail,
  PortfolioHealthResponse,
  PositionHealthItem,
} from '../types/api';

interface TargetListViewProps {
  onNavigateTab?: (tab: string, symbol?: string) => void;
}

export const TargetListView: React.FC<TargetListViewProps> = ({ onNavigateTab }) => {
  const [targetLists, setTargetLists] = useState<PortfolioSummary[]>([]);
  const [allPortfolios, setAllPortfolios] = useState<PortfolioSummary[]>([]);
  const [selectedListId, setSelectedListId] = useState<string>('targetlist_dips');
  const [activeListDetail, setActiveListDetail] = useState<PortfolioDetail | null>(null);
  const [holdings, setHoldings] = useState<UserHoldingItem[]>([]);
  const [healthReport, setHealthReport] = useState<PortfolioHealthResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Add to Wishlist Modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [addSymbol, setAddSymbol] = useState('');
  const [addShares, setAddShares] = useState('10');
  const [addPrice, setAddPrice] = useState('');
  const [addNotes, setAddNotes] = useState('');
  const [lookupPrice, setLookupPrice] = useState<number | null>(null);
  const [lookingUp, setLookingUp] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Create Target List Modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newListName, setNewListName] = useState('');
  const [newListDesc, setNewListDesc] = useState('');
  const [isCreatingList, setIsCreatingList] = useState(false);
  const [createListError, setCreateListError] = useState<string | null>(null);

  // Move to Live Portfolio Modal state
  const [moveToPortModalItem, setMoveToPortModalItem] = useState<PositionHealthItem | null>(null);
  const [destPortfolioId, setDestPortfolioId] = useState<string>('default');
  const [moveShares, setMoveShares] = useState<string>('10');
  const [moveBuyPrice, setMoveBuyPrice] = useState<string>('');
  const [isMoving, setIsMoving] = useState(false);

  // Filter
  const [filterTrigger, setFilterTrigger] = useState<'ALL' | 'READY' | 'WAITING'>('ALL');

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadLists();
  }, []);

  const loadLists = async (preferredId?: string) => {
    setLoading(true);
    setError(null);
    try {
      const all = await fetchPortfolios();
      setAllPortfolios(all);
      const lists = all.filter((p) => p.portfolio_type === 'TARGETLIST');
      setTargetLists(lists);

      let targetId = preferredId;
      if (!targetId || !lists.some((l) => l.id === targetId)) {
        targetId = lists.length > 0 ? lists[0].id : 'targetlist_dips';
      }
      setSelectedListId(targetId);
      await loadSpecificList(targetId);
    } catch (err: any) {
      setError(err.message || 'Failed to load target lists.');
    } finally {
      setLoading(false);
    }
  };

  const loadSpecificList = async (listId: string) => {
    try {
      const detail = await fetchPortfolio(listId);
      setActiveListDetail(detail);
      setHoldings(detail.holdings);
      if (detail.holdings && detail.holdings.length > 0) {
        const report = await evaluatePortfolioHealth(detail.holdings);
        setHealthReport(report);
      } else {
        setHealthReport(null);
      }
    } catch {
      // Graceful fallback
      setHealthReport(null);
    }
  };

  const handleSelectList = async (id: string) => {
    setSelectedListId(id);
    setLoading(true);
    try {
      await loadSpecificList(id);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTargetList = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newListName.trim()) {
      setCreateListError('Please enter a target list name.');
      return;
    }
    setIsCreatingList(true);
    setCreateListError(null);
    try {
      const created = await createPortfolio({
        name: newListName.trim(),
        description: newListDesc.trim() || undefined,
        portfolio_type: 'TARGETLIST',
      });
      setIsCreateModalOpen(false);
      setNewListName('');
      setNewListDesc('');
      await loadLists(created.id);
    } catch (err: any) {
      setCreateListError(err.message || 'Failed to create target list.');
    } finally {
      setIsCreatingList(false);
    }
  };

  const handleDeleteList = async () => {
    if (selectedListId === 'targetlist_dips') {
      alert('The core Tactical Dip Target List cannot be deleted.');
      return;
    }
    if (!window.confirm(`Are you sure you want to delete "${activeListDetail?.name || 'this list'}"?`)) {
      return;
    }
    try {
      await deletePortfolio(selectedListId);
      await loadLists('targetlist_dips');
    } catch (err: any) {
      setError(err.message || 'Failed to delete target list.');
    }
  };

  const handleLookupPrice = async (sym: string) => {
    const clean = sym.trim().toUpperCase();
    if (!clean) return;
    setLookingUp(true);
    try {
      const res = await analyzeStock(clean);
      setLookupPrice(res.current_price);
      if (!addPrice) {
        // Default target price to dip target if available, else current price
        const def = res.tactical_action?.dip_target_price && res.tactical_action.dip_target_price > 0
          ? res.tactical_action.dip_target_price
          : res.current_price;
        setAddPrice(def.toFixed(1));
      }
      if (!addNotes) {
        setAddNotes(`Target pullback entry near 50-DMA (Verdict: ${res.verdict_badge})`);
      }
    } catch {
      // Lookup failed
    } finally {
      setLookingUp(false);
    }
  };

  const handleAddStock = async (e: React.FormEvent) => {
    e.preventDefault();
    const sym = addSymbol.trim().toUpperCase();
    const sh = parseFloat(addShares);
    const pr = parseFloat(addPrice);

    if (!sym) {
      setAddError('Please enter a valid stock symbol.');
      return;
    }
    if (isNaN(sh) || sh <= 0) {
      setAddError('Please enter valid shares > 0.');
      return;
    }
    if (isNaN(pr) || pr <= 0) {
      setAddError('Please enter a target buy price > 0.');
      return;
    }

    setAddError(null);
    try {
      await addStockToPortfolio(selectedListId, {
        symbol: sym,
        shares: sh,
        buy_price: pr,
        target_price: pr,
        notes: addNotes.trim() || undefined,
      });
      setIsAddModalOpen(false);
      setAddSymbol('');
      setAddShares('10');
      setAddPrice('');
      setAddNotes('');
      setLookupPrice(null);
      await loadSpecificList(selectedListId);
      const all = await fetchPortfolios();
      setTargetLists(all.filter((p) => p.portfolio_type === 'TARGETLIST'));
    } catch (err: any) {
      setAddError(err.message || 'Failed to add stock to target list.');
    }
  };

  const handleRemoveStock = async (sym: string) => {
    try {
      const updated = holdings.filter((h) => h.symbol !== sym);
      setHoldings(updated);
      await savePortfolioHoldings(updated, selectedListId);
      await loadSpecificList(selectedListId);
      const all = await fetchPortfolios();
      setTargetLists(all.filter((p) => p.portfolio_type === 'TARGETLIST'));
    } catch (err: any) {
      setError(err.message || 'Failed to remove stock.');
    }
  };

  const handleOpenMoveModal = (pos: PositionHealthItem) => {
    setMoveToPortModalItem(pos);
    setMoveShares(pos.shares.toString());
    setMoveBuyPrice(pos.current_price.toFixed(1));
    const livePort = allPortfolios.find((p) => p.portfolio_type === 'PORTFOLIO');
    setDestPortfolioId(livePort ? livePort.id : 'default');
  };

  const handleConfirmMove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!moveToPortModalItem) return;
    const sh = parseFloat(moveShares);
    const pr = parseFloat(moveBuyPrice);
    if (isNaN(sh) || sh <= 0 || isNaN(pr) || pr <= 0) return;

    setIsMoving(true);
    try {
      await moveStockBetweenPortfolios(selectedListId, destPortfolioId, {
        symbol: moveToPortModalItem.symbol,
        shares: sh,
        buy_price: pr,
        target_price: moveToPortModalItem.target_price || undefined,
        notes: `Executed from Target List "${activeListDetail?.name}"`,
      });
      setMoveToPortModalItem(null);
      await loadSpecificList(selectedListId);
      const all = await fetchPortfolios();
      setTargetLists(all.filter((p) => p.portfolio_type === 'TARGETLIST'));
      setAllPortfolios(all);
    } catch (err: any) {
      alert(`Failed to move stock: ${err.message}`);
    } finally {
      setIsMoving(false);
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
        const prIdx = header.findIndex((h) => h.includes('price') || h.includes('target') || h.includes('buy') || h.includes('cost'));
        const noteIdx = header.findIndex((h) => h.includes('note') || h.includes('thesis'));

        if (symIdx === -1 || prIdx === -1) {
          setError('CSV must contain headers for Symbol and Target/Buy Price.');
          return;
        }

        const parsed: UserHoldingItem[] = [];
        for (let i = 1; i < lines.length; i++) {
          const row = lines[i].split(',').map((cell) => cell.trim());
          if (row.length <= Math.max(symIdx, prIdx)) continue;
          const s = row[symIdx]?.toUpperCase();
          const sh = shIdx !== -1 && !isNaN(parseFloat(row[shIdx])) ? parseFloat(row[shIdx]) : 10;
          const pr = parseFloat(row[prIdx]);
          const nt = noteIdx !== -1 && row[noteIdx] ? row[noteIdx] : undefined;
          if (s && !isNaN(pr) && pr > 0) {
            parsed.push({
              symbol: s,
              shares: sh,
              buy_price: pr,
              target_price: pr,
              notes: nt,
            });
          }
        }

        if (parsed.length > 0) {
          await savePortfolioHoldings(parsed, selectedListId);
          await loadSpecificList(selectedListId);
          const all = await fetchPortfolios();
          setTargetLists(all.filter((p) => p.portfolio_type === 'TARGETLIST'));
        }
      } catch (err: any) {
        setError('Error parsing CSV file: ' + err.message);
      }
    };
    reader.readAsText(file);
  };

  // KPI Calculations
  const positions = healthReport?.positions || [];
  const totalMonitored = holdings.length;
  const plannedCapital = positions.reduce((acc, p) => acc + p.shares * (p.target_price || p.buy_price), 0);

  // Ready in Buy Zone: CMP <= Target Price
  const readyPositions = positions.filter((p) => {
    const target = p.target_price || p.buy_price;
    return target > 0 && p.current_price <= target * 1.01; // within 1% or below
  });

  const waitingPositions = positions.filter((p) => {
    const target = p.target_price || p.buy_price;
    return target > 0 && p.current_price > target * 1.01;
  });

  const filteredPositions = positions.filter((p) => {
    const target = p.target_price || p.buy_price;
    const isReady = target > 0 && p.current_price <= target * 1.01;
    if (filterTrigger === 'READY') return isReady;
    if (filterTrigger === 'WAITING') return !isReady;
    return true;
  });

  return (
    <div className="space-y-8 animate-fadeIn text-slate-100 pb-16">
      {/* 1. Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-3xl bg-gradient-to-r from-[#0d1222] via-[#090d19] to-[#0d1222] border border-white/[0.08] shadow-2xl">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              <Target className="w-6 h-6 text-amber-400" />
              Tactical Target Lists & Wishlists
            </h1>
            <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 font-bold uppercase tracking-wider">
              DIP MONITORING
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Pre-commit watchlist for pullback accumulation • Distance-to-dip tracking • 1-click execution into live portfolio
          </p>
        </div>

        <div className="flex items-center space-x-3 flex-wrap">
          <input
            type="file"
            accept=".csv"
            ref={fileInputRef}
            onChange={handleCsvUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-semibold text-slate-200 transition-all cursor-pointer"
          >
            <Upload className="w-4 h-4 text-sky-400" />
            <span>Import CSV</span>
          </button>

          <button
            onClick={() => loadSpecificList(selectedListId)}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-semibold text-slate-200 transition-all cursor-pointer disabled:opacity-50"
            title="Refresh prices"
          >
            <RefreshCw className={`w-4 h-4 text-amber-400 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => {
              setAddError(null);
              setIsAddModalOpen(true);
            }}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-400 text-slate-950 text-xs font-bold shadow-lg shadow-amber-500/20 hover:brightness-110 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>+ Add to Wishlist</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 2. Target Lists Switcher Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-3xl bg-[#090d19] border border-white/[0.08] shadow-xl">
        <div className="flex items-center space-x-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5 px-2 shrink-0">
            <Layers className="w-4 h-4 text-amber-400" />
            <span>Target Lists:</span>
          </div>

          <div className="flex items-center gap-2 flex-nowrap">
            {targetLists.map((l) => {
              const isSelected = l.id === selectedListId;
              return (
                <button
                  key={l.id}
                  onClick={() => handleSelectList(l.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-2xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-lg shadow-amber-500/10'
                      : 'bg-white/[0.02] hover:bg-white/[0.05] text-slate-400 hover:text-slate-200 border border-white/[0.05]'
                  }`}
                >
                  <span>🎯</span>
                  <span>{l.name}</span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                      isSelected ? 'bg-amber-400/20 text-amber-200' : 'bg-white/[0.06] text-slate-400'
                    }`}
                  >
                    {l.holdings_count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
          <button
            onClick={() => {
              setCreateListError(null);
              setIsCreateModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-semibold text-slate-200 hover:text-white transition-colors cursor-pointer"
          >
            <FolderPlus className="w-4 h-4 text-amber-400" />
            <span>+ New Target List</span>
          </button>

          {selectedListId !== 'targetlist_dips' && (
            <button
              onClick={handleDeleteList}
              className="flex items-center gap-1.5 px-3 py-2 rounded-2xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-xs font-semibold text-rose-300 transition-colors cursor-pointer"
              title="Delete this target list"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete</span>
            </button>
          )}
        </div>
      </div>

      {/* 3. KPI Scorecards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-1 shadow-lg relative overflow-hidden">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5 text-amber-400" />
            Monitored Instruments
          </span>
          <div className="text-2xl font-black text-white tracking-tight">
            {totalMonitored} <span className="text-xs font-normal text-slate-500">equities & baskets</span>
          </div>
          <div className="text-xs text-slate-400 font-mono">
            In list: {activeListDetail?.name || 'Tactical Target List'}
          </div>
        </div>

        <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-1 shadow-lg relative overflow-hidden">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Coins className="w-3.5 h-3.5 text-sky-400" />
            Planned Capital Deployment
          </span>
          <div className="text-2xl font-black text-white font-mono tracking-tight">
            ₹{plannedCapital.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div className="text-xs text-slate-400 font-mono">
            Target capital required for accumulation
          </div>
        </div>

        <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-1 shadow-lg relative overflow-hidden">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            Ready in Buy Zone
          </span>
          <div className="text-2xl font-black text-emerald-400 font-mono tracking-tight">
            {readyPositions.length} <span className="text-xs text-slate-400 font-normal">triggers active</span>
          </div>
          <div className="text-xs text-emerald-400/80 font-mono">
            {readyPositions.length > 0 ? '✓ Live market price at or below dip target' : 'All waiting for deeper pullbacks'}
          </div>
        </div>

        <div className="p-5 rounded-3xl bg-[#090d19] border border-white/[0.08] space-y-1 shadow-lg relative overflow-hidden">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <SlidersHorizontal className="w-3.5 h-3.5 text-amber-400" />
            Awaiting Pullback
          </span>
          <div className="text-2xl font-black text-amber-300 font-mono tracking-tight">
            {waitingPositions.length} <span className="text-xs text-slate-400 font-normal">awaiting dip</span>
          </div>
          <div className="text-xs text-slate-400 font-mono">
            Monitoring technical 50-DMA support levels
          </div>
        </div>
      </div>

      {/* 4. Target List Blotter & Filter Bar */}
      <div className="p-6 rounded-3xl bg-[#090d19] border border-white/[0.08] shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <BookmarkPlus className="w-5 h-5 text-amber-400" />
              Watchlist Holdings & Dip Proximity
            </h2>
            <p className="text-xs text-slate-400">
              Real-time monitoring of live market price vs your accumulation target.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400">Filter:</span>
            <div className="flex items-center p-1 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs font-mono">
              <button
                onClick={() => setFilterTrigger('ALL')}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  filterTrigger === 'ALL'
                    ? 'bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                All ({positions.length})
              </button>
              <button
                onClick={() => setFilterTrigger('READY')}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  filterTrigger === 'READY'
                    ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                In Buy Zone ({readyPositions.length})
              </button>
              <button
                onClick={() => setFilterTrigger('WAITING')}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  filterTrigger === 'WAITING'
                    ? 'bg-sky-500/20 text-sky-300 font-bold border border-sky-500/30'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Awaiting Dip ({waitingPositions.length})
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-amber-500/20 border-t-amber-400 rounded-full animate-spin" />
            <p className="text-xs font-mono text-slate-400">Auditing live market prices and distance to dip targets...</p>
          </div>
        ) : filteredPositions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[10px] font-mono text-slate-400 uppercase tracking-wider border-b border-white/[0.06]">
                <tr>
                  <th className="py-3 px-3">Symbol & Sector</th>
                  <th className="py-3 px-3">Live CMP</th>
                  <th className="py-3 px-3">Target Price</th>
                  <th className="py-3 px-3">Dip Distance</th>
                  <th className="py-3 px-3">Planned Qty</th>
                  <th className="py-3 px-3">Est. Capital</th>
                  <th className="py-3 px-3">Tactical Notes & Rationale</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] font-mono">
                {filteredPositions.map((p) => {
                  const target = p.target_price || p.buy_price;
                  const distancePct = target > 0 ? ((p.current_price - target) / target) * 100 : 0;
                  const isReady = target > 0 && p.current_price <= target * 1.01;

                  return (
                    <tr key={p.symbol} className="hover:bg-white/[0.02] transition-colors">
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

                      <td className="py-3.5 px-3">
                        <div className="text-white font-bold">₹{p.current_price.toFixed(1)}</div>
                        <span className="text-[10px] text-slate-400">Live Quote</span>
                      </td>

                      <td className="py-3.5 px-3">
                        <div className="text-amber-300 font-bold">₹{target.toFixed(1)}</div>
                        <span className="text-[10px] text-slate-500">Accumulation Limit</span>
                      </td>

                      <td className="py-3.5 px-3">
                        {isReady ? (
                          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 w-fit">
                            <Check className="w-3 h-3" />
                            <span>IN BUY ZONE ({distancePct.toFixed(1)}%)</span>
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20 flex items-center gap-1 w-fit">
                            <span>WAITING (+{distancePct.toFixed(1)}%)</span>
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-3 text-slate-300 font-semibold">
                        {p.shares.toFixed(0)} sh
                      </td>

                      <td className="py-3.5 px-3 text-white font-bold">
                        ₹{(p.shares * target).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </td>

                      <td className="py-3.5 px-3 font-sans text-xs text-slate-300 max-w-xs">
                        <p className="truncate" title={p.notes || p.action_rationale}>
                          {p.notes || p.action_rationale || 'Tactical dip accumulation'}
                        </p>
                      </td>

                      <td className="py-3.5 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Analyze in Stock Analyzer */}
                          <button
                            onClick={() => onNavigateTab && onNavigateTab('analyzer', p.symbol)}
                            className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-white transition-colors cursor-pointer"
                            title="Analyze in Stock Analyzer"
                          >
                            <Search className="w-3.5 h-3.5 text-sky-400" />
                          </button>

                          {/* Move to Live Portfolio */}
                          <button
                            onClick={() => handleOpenMoveModal(p)}
                            className="p-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 transition-colors cursor-pointer"
                            title="Execute & Move to Live Portfolio"
                          >
                            <Briefcase className="w-3.5 h-3.5" />
                          </button>

                          {/* Delete */}
                          <button
                            onClick={() => handleRemoveStock(p.symbol)}
                            className="p-1.5 rounded-lg hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                            title="Remove from target list"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-16 text-center space-y-3">
            <Target className="w-12 h-12 text-slate-600 mx-auto" />
            <div className="text-white font-bold text-sm">No stocks recorded in this target list</div>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Add stocks directly from the Stock Analyzer using "Add to Wishlist", or click "+ Add to Wishlist" above.
            </p>
            <button
              onClick={() => {
                setAddError(null);
                setIsAddModalOpen(true);
              }}
              className="px-4 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold cursor-pointer"
            >
              + Add First Instrument
            </button>
          </div>
        )}
      </div>

      {/* 5. ADD TO WISHLIST / TARGET LIST MODAL */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-md rounded-3xl bg-[#090d19] border border-white/[0.12] p-6 shadow-2xl space-y-4 text-slate-100">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <BookmarkPlus className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Add Stock to Wishlist</h3>
                  <p className="text-xs text-slate-400">Set dip accumulation limits and notes</p>
                </div>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="p-1.5 rounded-xl hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {addError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{addError}</span>
              </div>
            )}

            <form onSubmit={handleAddStock} className="space-y-3.5 font-sans text-xs">
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  Symbol (NSE)
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={addSymbol}
                    onChange={(e) => setAddSymbol(e.target.value.toUpperCase())}
                    onBlur={() => handleLookupPrice(addSymbol)}
                    placeholder="e.g. TCS, RELIANCE, NIFTYBEES"
                    className="flex-1 px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white font-mono uppercase focus:outline-none focus:border-amber-400 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => handleLookupPrice(addSymbol)}
                    disabled={lookingUp || !addSymbol}
                    className="px-3 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-mono text-slate-300 hover:text-white border border-white/[0.1] cursor-pointer disabled:opacity-50"
                  >
                    {lookingUp ? '...' : 'Lookup'}
                  </button>
                </div>
                {lookupPrice && (
                  <span className="text-[10px] text-emerald-400 font-mono mt-1 block">
                    ✓ Live CMP: ₹{lookupPrice.toFixed(1)}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Planned Shares
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={addShares}
                    onChange={(e) => setAddShares(e.target.value)}
                    placeholder="10"
                    className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white font-mono focus:outline-none focus:border-amber-400 transition-colors"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Target Buy Price (₹)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={addPrice}
                    onChange={(e) => setAddPrice(e.target.value)}
                    placeholder="e.g. 1350"
                    className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white font-mono focus:outline-none focus:border-amber-400 transition-colors"
                  />
                </div>
              </div>

              {lookupPrice && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setAddPrice(lookupPrice.toFixed(1))}
                    className="text-[10px] font-mono text-slate-400 hover:text-white px-2 py-0.5 rounded bg-white/[0.03] border border-white/[0.06]"
                  >
                    Use CMP (₹{lookupPrice.toFixed(1)})
                  </button>
                  <button
                    type="button"
                    onClick={() => setAddPrice((lookupPrice * 0.95).toFixed(1))}
                    className="text-[10px] font-mono text-amber-300 hover:text-amber-200 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20"
                  >
                    -5% Dip (₹{(lookupPrice * 0.95).toFixed(1)})
                  </button>
                </div>
              )}

              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  Tactical Notes & Conviction Thesis
                </label>
                <textarea
                  rows={2}
                  value={addNotes}
                  onChange={(e) => setAddNotes(e.target.value)}
                  placeholder="e.g. Accumulate only when RSI < 40 near 50-DMA"
                  className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-amber-400 transition-colors font-sans"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold text-slate-300 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-400 hover:brightness-110 text-slate-950 font-bold text-xs font-mono transition-all shadow-lg shadow-amber-500/20 cursor-pointer"
                >
                  Add to List
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 6. CREATE TARGET LIST MODAL */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-md rounded-3xl bg-[#090d19] border border-white/[0.12] p-6 shadow-2xl space-y-4 text-slate-100">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <FolderPlus className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Create Target List</h3>
                  <p className="text-xs text-slate-400">Create a dedicated wishlist for pullbacks</p>
                </div>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="p-1.5 rounded-xl hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {createListError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{createListError}</span>
              </div>
            )}

            <form onSubmit={handleCreateTargetList} className="space-y-3.5 font-sans text-xs">
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  List Name *
                </label>
                <input
                  type="text"
                  value={newListName}
                  onChange={(e) => setNewListName(e.target.value)}
                  placeholder="e.g. Q4 High-Beta Dips"
                  className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-amber-400 transition-colors"
                />
              </div>

              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  Description (Optional)
                </label>
                <input
                  type="text"
                  value={newListDesc}
                  onChange={(e) => setNewListDesc(e.target.value)}
                  placeholder="e.g. Tech compounders to accumulate on market pullbacks"
                  className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-amber-400 transition-colors"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  disabled={isCreatingList}
                  className="px-4 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold text-slate-300 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingList}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-400 hover:brightness-110 text-slate-950 font-bold text-xs font-mono transition-all shadow-lg shadow-amber-500/20 cursor-pointer disabled:opacity-50"
                >
                  {isCreatingList ? 'Creating...' : 'Create List'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 7. MOVE TO LIVE PORTFOLIO MODAL */}
      {moveToPortModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-md rounded-3xl bg-[#090d19] border border-white/[0.12] p-6 shadow-2xl space-y-4 text-slate-100">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <Briefcase className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Execute into Live Portfolio</h3>
                  <p className="text-xs text-slate-400">
                    Move {moveToPortModalItem.symbol} from watchlist to active holdings
                  </p>
                </div>
              </div>
              <button
                onClick={() => setMoveToPortModalItem(null)}
                className="p-1.5 rounded-xl hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleConfirmMove} className="space-y-3.5 font-sans text-xs">
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                  Destination Live Portfolio
                </label>
                <select
                  value={destPortfolioId}
                  onChange={(e) => setDestPortfolioId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-amber-400 transition-colors"
                >
                  {allPortfolios
                    .filter((p) => p.portfolio_type === 'PORTFOLIO')
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.holdings_count} holdings)
                      </option>
                    ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Purchased Shares
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={moveShares}
                    onChange={(e) => setMoveShares(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white font-mono focus:outline-none focus:border-amber-400 transition-colors"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                    Actual Executed Price (₹)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={moveBuyPrice}
                    onChange={(e) => setMoveBuyPrice(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#060810] border border-white/[0.1] text-xs text-white font-mono focus:outline-none focus:border-amber-400 transition-colors"
                  />
                </div>
              </div>

              <div className="p-3 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20 text-xs text-emerald-300">
                This will add {moveToPortModalItem.symbol} to your active portfolio capital calculation and remove it from this target list.
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setMoveToPortModalItem(null)}
                  disabled={isMoving}
                  className="px-4 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold text-slate-300 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isMoving}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-400 hover:brightness-110 text-slate-950 font-bold text-xs font-mono transition-all shadow-lg shadow-emerald-500/20 cursor-pointer disabled:opacity-50"
                >
                  {isMoving ? 'Moving...' : 'Confirm Execution'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
