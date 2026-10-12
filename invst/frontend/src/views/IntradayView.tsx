// IIM — Main Intraday Intelligence View
// 3-panel layout: stock tiles → live chart → signal cards + accuracy

import { useState, useEffect, useRef, useCallback } from 'react';
import IntradayChart from '../components/IntradayChart';
import IntradaySignalCard from '../components/IntradaySignalCard';
import type {
  IntradaySignal, IntradayStockItem, ChartData, RegimeState, SSEEvent,
} from '../types/intraday';
import { apiUrl, authenticatedApiFetch } from '../api/client';

const API = '/api/v1/intraday';

// ── Regime badge ───────────────────────────────────────────────────────────
function RegimeBadge({ regime }: { regime: RegimeState | null }) {
  if (!regime) return null;
  const colors: Record<string, string> = {
    TRENDING_BULL: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    TRENDING_BEAR: 'bg-red-500/10 text-red-400 border-red-500/30',
    AMBIGUOUS:     'bg-amber-500/10 text-amber-400 border-amber-500/30',
    RANGING:       'bg-slate-600/10 text-slate-400 border-slate-600/30',
    AVOID:         'bg-red-900/20 text-red-300 border-red-700/40',
  };
  const icons: Record<string, string> = {
    TRENDING_BULL: '📈', TRENDING_BEAR: '📉',
    AMBIGUOUS: '〰️', RANGING: '↔️', AVOID: '🚫',
  };
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${colors[regime.regime] ?? ''}`}>
      {icons[regime.regime]} {regime.regime.replace('_', ' ')}
      <span className="ml-1.5 text-xs opacity-70">ADX {regime.adx.toFixed(0)} | VIX {regime.india_vix.toFixed(1)}</span>
    </span>
  );
}

// ── Stock tile ─────────────────────────────────────────────────────────────
function StockTile({
  stock, signals, selected, onClick,
}: {
  stock: IntradayStockItem;
  signals: IntradaySignal[];
  selected: boolean;
  onClick: () => void;
}) {
  const stockSignals = signals.filter(s => s.symbol === stock.symbol && ['PENDING','ENTRY_FILLED'].includes(s.current_status));
  const hasLong = stockSignals.some(s => s.signal_type === 'LONG');
  const hasShort = stockSignals.some(s => s.signal_type === 'SHORT');
  const gapColor = stock.gap_type === 'GAP_UP' ? 'text-emerald-400' : stock.gap_type === 'GAP_DOWN' ? 'text-red-400' : 'text-slate-500';

  return (
    <button
      onClick={onClick}
      className={`rounded-xl border p-3 text-left transition-all hover:border-indigo-500/50 ${
        selected ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-700/60 bg-slate-900/40'
      }`}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-mono font-bold text-white text-sm">{stock.symbol}</span>
        {hasLong && <span className="text-emerald-400 text-xs font-bold">▲ BUY</span>}
        {hasShort && <span className="text-red-400 text-xs font-bold">▼ SELL</span>}
        {!hasLong && !hasShort && <span className="text-slate-500 text-xs">WATCH</span>}
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span className="text-indigo-400 font-mono">ISS {stock.iss_score?.toFixed(0)}</span>
        <span className={`font-mono ${gapColor}`}>{stock.gap_type ?? 'FLAT'}</span>
      </div>
    </button>
  );
}

// ── Main view ──────────────────────────────────────────────────────────────
export default function IntradayView() {
  const [universe, setUniverse] = useState<IntradayStockItem[]>([]);
  const [signals, setSignals] = useState<IntradaySignal[]>([]);
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [regime, setRegime] = useState<RegimeState | null>(null);
  const [accuracy, setAccuracy] = useState<any>(null);
  const [feedMode, setFeedMode] = useState<'live' | 'paper' | null>(null);
  const [feedReceiving, setFeedReceiving] = useState(false);
  const [marketHours, setMarketHours] = useState(false);
  const [instrumentTab, setInstrumentTab] = useState<'stocks' | 'options'>('stocks');
  const [apiError, setApiError] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'active' | 'history'>('active');
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // ── Fetch universe ──────────────────────────────────────────────────────
  const fetchUniverse = useCallback(async () => {
    try {
      const res = await authenticatedApiFetch(`${API}/universe`);
      if (!res.ok) throw new Error(`universe request returned ${res.status}`);
      const data = await res.json();
      setUniverse(data.stocks ?? []);
      if (!selectedSymbol && data.stocks?.length > 0) {
        setSelectedSymbol(data.stocks[0].symbol);
      }
    } catch (error) { setApiError(error instanceof Error ? error.message : 'connection failed'); }
  }, [selectedSymbol]);

  // ── Fetch signals ───────────────────────────────────────────────────────
  const fetchSignals = useCallback(async (hist = false, mode: 'live' | 'paper' = feedMode || 'live') => {
    try {
      const res = await authenticatedApiFetch(`${API}/signals?history=${hist}&mode=${mode}`);
      if (!res.ok) throw new Error(`signals request returned ${res.status}`);
      const data = await res.json();
      setSignals(data.signals ?? []);
    } catch (error) { setApiError(error instanceof Error ? error.message : 'connection failed'); }
  }, [feedMode]);

  // ── Fetch chart data ────────────────────────────────────────────────────
  const fetchChart = useCallback(async (symbol: string) => {
    try {
      const res = await authenticatedApiFetch(`${API}/chart/${encodeURIComponent(symbol)}?n=120`);
      if (!res.ok) throw new Error(`chart request returned ${res.status}`);
      setChartData(await res.json());
    } catch (error) { setApiError(error instanceof Error ? error.message : 'connection failed'); }
  }, []);

  // ── Fetch regime ────────────────────────────────────────────────────────
  const fetchRegime = useCallback(async () => {
    try {
      const res = await authenticatedApiFetch(`${API}/regime`);
      if (!res.ok) throw new Error(`market regime request returned ${res.status}`);
      setRegime(await res.json());
    } catch (error) { setApiError(error instanceof Error ? error.message : 'connection failed'); }
  }, []);

  const fetchAccuracy = useCallback(async (mode: 'live' | 'paper' = feedMode || 'live') => {
    try {
      const res = await authenticatedApiFetch(`${API}/accuracy?mode=${mode}`);
      if (res.ok) setAccuracy(await res.json());
    } catch { /* accuracy remains explicitly unavailable */ }
  }, [feedMode]);

  const fetchFeedStatus = useCallback(async () => {
    try {
      const res = await authenticatedApiFetch(`${API}/status`);
      if (!res.ok) return feedMode;
      const status = await res.json();
      const mode = status.mode === 'live' || status.mode === 'paper' ? status.mode : null;
      if (mode) setApiError(null);
      setFeedMode(mode);
      setFeedReceiving(Boolean(status.receiving));
      setMarketHours(Boolean(status.market_hours));
      return mode;
    } catch { return feedMode; }
  }, [feedMode]);

  // ── SSE connection ──────────────────────────────────────────────────────
  useEffect(() => {
    const es = new EventSource(apiUrl(`${API}/stream`));
    eventSourceRef.current = es;

    es.onopen = () => setIsConnected(true);
    es.onerror = () => setIsConnected(false);

    es.onmessage = (e: MessageEvent) => {
      try {
        const event: SSEEvent = JSON.parse(e.data);
        if (event.type === 'SIGNAL_NEW') {
          setSignals(prev => [event.data, ...prev]);
        } else if (event.type === 'SIGNAL_UPDATE') {
          setSignals(prev => prev.map(s =>
            s.id === event.signal_id
              ? { ...s, current_status: event.status, exit_price: event.exit_price } as IntradaySignal
              : s
          ));
        } else if (event.type === 'CANDLE_UPDATE' && event.symbol === selectedSymbol) {
          setChartData(prev => {
            if (!prev) return prev;
            return { ...prev, candles: [...prev.candles.slice(-119), event.data] };
          });
        }
      } catch { /* invalid JSON */ }
    };

    return () => { es.close(); setIsConnected(false); };
  }, [selectedSymbol]);

  // ── Initial load ────────────────────────────────────────────────────────
  useEffect(() => {
    fetchUniverse();
    fetchRegime();
    fetchFeedStatus().then((mode) => {
      if (mode) {
        fetchSignals(activeTab === 'history', mode);
        fetchAccuracy(mode);
      } else {
        setApiError('Intraday scheduler is not available. Check that the backend and market-data feed are running.');
      }
    });
    const interval = setInterval(async () => {
      fetchRegime();
      const mode = await fetchFeedStatus();
      if (mode) { fetchSignals(activeTab === 'history', mode); fetchAccuracy(mode); }
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedSymbol) fetchChart(selectedSymbol);
  }, [selectedSymbol]);

  // ── Signal feedback ─────────────────────────────────────────────────────
  const handleFeedback = async (signalId: number, eventType: string) => {
    try {
      await authenticatedApiFetch(`${API}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signal_id: signalId, event_type: eventType }),
      });
      await fetchSignals(activeTab === 'history');
    } catch { /* silent */ }
  };

  const symbolSignals = signals.filter(s => s.symbol === selectedSymbol);
  const activeSignals = signals.filter(s => ['PENDING','ENTRY_FILLED'].includes(s.current_status));

  return (
    <div className="intraday-workspace flex flex-col gap-5 py-2 text-slate-200">

      {/* ── Header bar ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-white tracking-tight">
            Intraday Market Signals
          </h1>
          <span className={`text-xs px-2 py-0.5 rounded-full border font-mono ${
            isConnected
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-slate-800 text-slate-500 border-slate-700'
          }`}>
            {feedMode === 'paper' ? 'STUDY · DELAYED' : feedMode === 'live' && feedReceiving ? 'LIVE FEED' : isConnected ? 'STREAM CONNECTED' : 'FEED UNAVAILABLE'}
          </span>
          <RegimeBadge regime={regime} />
        </div>
        <div className="text-right text-xs text-slate-500">
          <div>{universe.length} stocks selected · {activeSignals.length} active signals</div>
          <div className="mt-1">{marketHours ? 'NSE session open' : 'Outside NSE session'} · {feedMode === 'paper' ? 'delayed study data' : feedMode === 'live' ? 'broker feed configured' : 'feed status unknown'}</div>
        </div>
      </div>

      <section className="intraday-market-status rounded-2xl border border-white/10 bg-slate-900/40 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[.16em] text-slate-500">Session coverage</div>
            <p className="mt-1 text-sm text-slate-300">NSE cash equities · closed 15-minute candles · signals require confirmation gates</p>
          </div>
          <div className="flex rounded-xl border border-white/10 bg-slate-950/40 p-1" role="tablist" aria-label="Intraday instrument">
            <button type="button" onClick={() => setInstrumentTab('stocks')} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${instrumentTab === 'stocks' ? 'bg-[#53654b] text-white' : 'text-slate-400'}`}>Stocks</button>
            <button type="button" onClick={() => setInstrumentTab('options')} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${instrumentTab === 'options' ? 'bg-[#53654b] text-white' : 'text-slate-400'}`}>Options</button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3" aria-label="Measured signal record">
        <div className="rounded-2xl border border-white/10 bg-slate-900/35 p-4"><span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Live strategy sample</span><strong className="mt-1 block font-mono text-xl text-white">{accuracy?.total_trades ?? '—'}</strong><span className="text-xs text-slate-500">closed trades recorded</span></div>
        <div className="rounded-2xl border border-white/10 bg-slate-900/35 p-4"><span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Observed win rate</span><strong className="mt-1 block font-mono text-xl text-white">{accuracy && accuracy.total_trades > 0 ? `${(accuracy.win_rate * 100).toFixed(1)}%` : 'Not established'}</strong><span className="text-xs text-slate-500">{accuracy?.data_source_note || 'Shown only after outcomes are recorded'}</span></div>
        <div className="rounded-2xl border border-white/10 bg-slate-900/35 p-4"><span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Confidence interval</span><strong className="mt-1 block font-mono text-xl text-white">{accuracy && accuracy.total_trades > 0 ? `${(accuracy.ci_lower * 100).toFixed(0)}–${(accuracy.ci_upper * 100).toFixed(0)}%` : 'Insufficient sample'}</strong><span className="text-xs text-slate-500">No win rate or 2–5% move is guaranteed</span></div>
      </section>

      {apiError && <p role="alert" className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-3 text-sm text-rose-700">Intraday data could not be loaded: {apiError}</p>}

      {instrumentTab === 'options' ? (
        <section className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-6">
          <div className="text-[10px] font-bold uppercase tracking-[.16em] text-amber-700">Options coverage unavailable</div>
          <h2 className="mt-2 text-lg font-semibold text-slate-900">A live option chain is not connected</h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">This backend currently supplies equity candles only. It has no option-chain, contract quote, implied-volatility or Greeks feed, so Arth IQ cannot calculate option entries, stops, or outcomes reliably. Connect a supported market-data source before enabling options signals.</p>
        </section>
      ) : <>

      {/* ── Stock tiles ── */}
      {universe.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-7 gap-2">
          {universe.map(stock => (
            <StockTile
              key={stock.symbol}
              stock={stock}
              signals={signals}
              selected={selectedSymbol === stock.symbol}
              onClick={() => setSelectedSymbol(stock.symbol)}
            />
          ))}
        </div>
      )}

      {universe.length === 0 && instrumentTab === 'stocks' && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 text-center text-slate-500">
          <p className="text-sm">No stocks selected yet.</p>
          <p className="text-xs mt-1">The morning scan runs at 8:45 AM IST and selects today's universe.</p>
        </div>
      )}

      {/* ── Main 2-col layout: Chart | Signals ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Chart (2/3 width) */}
        <div className="lg:col-span-2">
          {selectedSymbol ? (
            <IntradayChart
              chartData={chartData}
              signals={symbolSignals}
              symbol={selectedSymbol}
              height={460}
            />
          ) : (
            <div className="h-[460px] rounded-xl border border-slate-800 bg-slate-900/40 flex items-center justify-center text-slate-500">
              Select a stock above to view chart
            </div>
          )}
        </div>

        {/* Signal panel (1/3 width) */}
        <div className="flex flex-col gap-3">
          {/* Tab switch */}
          <div className="flex gap-1 rounded-lg bg-slate-900/60 p-1 border border-slate-800">
            {(['active', 'history'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => { setActiveTab(tab); fetchSignals(tab === 'history'); }}
                className={`flex-1 text-xs py-1.5 rounded-md font-medium transition-colors ${
                  activeTab === tab
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab === 'active' ? `Active (${activeSignals.length})` : 'Today\'s History'}
              </button>
            ))}
          </div>

          {/* Signal cards */}
          <div className="flex flex-col gap-3 max-h-[420px] overflow-y-auto pr-1">
            {(activeTab === 'active' ? activeSignals : signals).length === 0 ? (
              <div className="text-center text-slate-500 text-sm py-8">
                <p>No {activeTab === 'active' ? 'active' : ''} signals yet.</p>
                {activeTab === 'active' && (
                  <p className="text-xs mt-1">Signals appear when all 4 pillars confirm.</p>
                )}
              </div>
            ) : (
              (activeTab === 'active' ? activeSignals : signals).map(signal => (
                <IntradaySignalCard
                  key={signal.id}
                  signal={signal}
                  accountCapital={500000}
                  onFeedback={handleFeedback}
                />
              ))
            )}
          </div>
        </div>
      </div>
      </>}

      {/* ── Disclaimer ── */}
      <p className="text-xs text-slate-700 text-center mt-2">
        ArthIQ Intraday signals are for decision support only. Not financial advice.
        All signals require manual execution via your broker. Past accuracy does not guarantee future performance.
      </p>
    </div>
  );
}
