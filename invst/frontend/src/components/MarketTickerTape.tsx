import React, { useEffect, useState } from 'react';
import { TrendingDown, TrendingUp, Radio } from 'lucide-react';
import { fetchMarketTickerTape } from '../api/client';
import { TickerItem } from '../types/api';

type FeedState = 'loading' | 'live' | 'snapshot' | 'mixed' | 'stale' | 'unavailable';

const formatAsOf = (value?: string): string => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    hour: value.includes('T') ? '2-digit' : undefined,
    minute: value.includes('T') ? '2-digit' : undefined,
  }).format(date);
};

export const MarketTickerTape: React.FC = () => {
  const [tickers, setTickers] = useState<TickerItem[]>([]);
  const [feedState, setFeedState] = useState<FeedState>('loading');

  useEffect(() => {
    let isMounted = true;
    let requestPending = false;

    const loadData = async () => {
      if (requestPending || document.visibilityState === 'hidden') return;
      requestPending = true;
      try {
        const data = await fetchMarketTickerTape();
        if (!isMounted) return;
        const usable = data.filter((item) => item.price_source !== 'unavailable');
        setTickers(usable);
        if (usable.length === 0) {
          setFeedState('unavailable');
        } else {
          const liveCount = usable.filter((item) => item.is_live === true).length;
          setFeedState(liveCount === usable.length ? 'live' : liveCount > 0 ? 'mixed' : 'snapshot');
        }
      } catch {
        if (isMounted) setFeedState(tickers.length > 0 ? 'stale' : 'unavailable');
      } finally {
        requestPending = false;
      }
    };

    void loadData();
    const intervalId = window.setInterval(loadData, 60_000);
    document.addEventListener('visibilitychange', loadData);
    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', loadData);
    };
  }, [tickers.length]);

  const stateLabel: Record<FeedState, string> = {
    loading: 'Loading quotes',
    live: 'Live quotes',
    snapshot: 'Daily close',
    mixed: 'Mixed sources',
    stale: 'Last update failed',
    unavailable: 'Market data unavailable',
  };
  const asOfValues = tickers.map((item) => item.last_updated).filter(Boolean).sort();
  const latestAsOf = asOfValues[asOfValues.length - 1];
  const tapeItems = tickers.length > 1 && feedState !== 'stale' ? [...tickers, ...tickers] : tickers;

  return (
    <div className="relative z-10 w-full bg-[#05070c]/90 backdrop-blur-md border-y border-white/[0.06] overflow-hidden ticker-tape-container py-1.5 text-xs select-none">
      <div className="flex min-w-0 items-center min-h-8">
        <div
          className="relative flex items-center gap-1.5 px-3 py-1 border-r border-white/[0.08] text-slate-300 font-bold tracking-wide text-[10px] shrink-0"
          title={latestAsOf ? `Quote data as of ${formatAsOf(latestAsOf)} India time` : stateLabel[feedState]}
          aria-live="polite"
        >
          <span className={`inline-flex rounded-full h-1.5 w-1.5 ${feedState === 'live' ? 'bg-emerald-400' : feedState === 'unavailable' || feedState === 'stale' ? 'bg-amber-400' : 'bg-slate-400'}`} />
          <Radio className="w-3 h-3 text-winsor-400" />
          <span>{stateLabel[feedState]}</span>
          {latestAsOf && <span className="ticker-asof text-[9px] text-slate-500 font-normal">As of {formatAsOf(latestAsOf)}</span>}
        </div>

        {tapeItems.length > 0 ? (
          <div className="min-w-0 flex-1 overflow-hidden">
          <div className={`flex w-max space-x-6 whitespace-nowrap pl-6 ${tapeItems.length > tickers.length ? 'animate-marquee' : ''}`}>
            {tapeItems.map((item, idx) => {
              const positive = item.isPositive;
              const TrendIcon = positive ? TrendingUp : TrendingDown;
              const quoteSource = item.is_live ? 'Live quote' : `Daily close${item.last_updated ? ` · ${formatAsOf(item.last_updated)}` : ''}`;
              return (
                <div
                  key={`${item.symbol}-${idx}`}
                  title={`${quoteSource}${item.raw_symbol ? ` · ${item.raw_symbol}` : ''}`}
                  className="inline-flex items-center gap-2 font-mono px-2 py-0.5 rounded-lg hover:bg-white/[0.05] border border-transparent hover:border-white/[0.08] transition-colors"
                >
                  <span className="text-slate-300 font-semibold">{item.symbol}</span>
                  <span className="text-white font-bold">{item.price}</span>
                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-bold ${positive ? 'text-emerald-300 bg-emerald-950/50 border border-emerald-500/20' : 'text-rose-300 bg-rose-950/50 border border-rose-500/20'}`}>
                    <TrendIcon className="w-2.5 h-2.5 mr-0.5" />{item.change}
                  </span>
                  {!item.is_live && <span className="text-[9px] text-slate-500">EOD</span>}
                </div>
              );
            })}
          </div>
          </div>
        ) : (
          <span className="pl-4 text-[11px] text-slate-500">
            {feedState === 'loading' ? 'Connecting to quote service…' : 'No quote values are being shown until data is available.'}
          </span>
        )}
      </div>
    </div>
  );
};
