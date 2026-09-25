import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Radio } from 'lucide-react';
import { fetchMarketTickerTape } from '../api/client';
import { TickerItem } from '../types/api';

const DEFAULT_TICKERS: TickerItem[] = [
  { symbol: 'NIFTY 50', price: '24,835.40', change: '+0.48%', isPositive: true },
  { symbol: 'SENSEX', price: '81,382.10', change: '+0.52%', isPositive: true },
  { symbol: 'BANK NIFTY', price: '51,240.85', change: '+0.31%', isPositive: true },
  { symbol: 'INDIA VIX', price: '12.84', change: '-3.12%', isPositive: false },
  { symbol: 'RELIANCE', price: '₹1,247.40', change: '+1.24%', isPositive: true },
  { symbol: 'TCS', price: '₹2,082.00', change: '-0.24%', isPositive: false },
  { symbol: 'HDFCBANK', price: '₹728.90', change: '-1.43%', isPositive: false },
  { symbol: 'INFY', price: '₹1,014.50', change: '-2.31%', isPositive: false },
  { symbol: 'ICICIBANK', price: '₹1,334.50', change: '+0.85%', isPositive: true },
  { symbol: 'USD/INR', price: '83.52', change: '+0.04%', isPositive: true },
  { symbol: 'GOLD BEES', price: '₹123.48', change: '+0.25%', isPositive: true },
  { symbol: 'SILVER BEES', price: '₹162.55', change: '+0.45%', isPositive: true },
  { symbol: 'NIFTY BEES', price: '₹264.13', change: '+0.05%', isPositive: true },
];

export const MarketTickerTape: React.FC = () => {
  const [tickers, setTickers] = useState<TickerItem[]>(DEFAULT_TICKERS);
  const [isLive, setIsLive] = useState<boolean>(true);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      try {
        const data = await fetchMarketTickerTape();
        if (isMounted && data && data.length > 0) {
          setTickers(data);
          setIsLive(true);
          const now = new Date();
          setLastUpdated(now.toLocaleTimeString('en-IN', { hour12: false }));
        }
      } catch (err) {
        // Fallback silently to existing tickers
        if (isMounted) setIsLive(false);
      }
    };

    loadData();
    // Poll every 15 seconds for real-time live price updates
    const intervalId = setInterval(loadData, 15000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  // Duplicate array to enable seamless marquee looping
  const tapeItems = [...tickers, ...tickers];

  return (
    <div className="relative w-full bg-[#05070c]/90 backdrop-blur-md border-y border-white/[0.06] overflow-hidden ticker-tape-container py-2 text-xs select-none">
      {/* Edge gradient fade masks for seamless floating appearance */}
      <div className="pointer-events-none absolute left-28 top-0 bottom-0 w-12 bg-gradient-to-r from-[#05070c] to-transparent z-10" />
      <div className="pointer-events-none absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-[#05070c] to-transparent z-10" />

      <div className="flex items-center">
        {/* Static live badge with pulsing radar beacon */}
        <div
          className="relative flex items-center space-x-1.5 px-3 py-1 bg-gradient-to-r from-winsor-950 to-slate-950 border-r border-winsor-800/40 text-winsor-400 font-bold tracking-wider text-[10px] shrink-0 z-20 shadow-[4px_0_12px_rgba(0,0,0,0.5)]"
          title={lastUpdated ? `Live quotes refreshed at ${lastUpdated}` : 'Real-time NSE stream'}
        >
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isLive ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isLive ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </span>
          <Radio className={`w-3 h-3 ${isLive ? 'text-sky-400' : 'text-amber-400'}`} />
          <span className="font-mono">NSE LIVE</span>
          {lastUpdated && (
            <span className="text-[9px] font-mono text-slate-500 hidden sm:inline ml-1 font-normal">
              {lastUpdated}
            </span>
          )}
        </div>

        {/* Scrolling marquee */}
        <div className="flex space-x-6 animate-marquee whitespace-nowrap pl-6">
          {tapeItems.map((item, idx) => {
            const TrendIcon = item.isPositive ? TrendingUp : TrendingDown;
            return (
              <div
                key={`${item.symbol}-${idx}`}
                className="inline-flex items-center space-x-2 font-mono px-2 py-0.5 rounded-lg hover:bg-white/[0.05] border border-transparent hover:border-white/[0.08] transition-all cursor-default"
              >
                <span className="text-slate-300 font-semibold text-xs">{item.symbol}</span>
                <span className="text-white font-bold text-xs">{item.price}</span>
                <span
                  className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-bold ${
                    item.isPositive
                      ? 'text-emerald-300 bg-emerald-950/60 border border-emerald-500/20'
                      : 'text-rose-300 bg-rose-950/60 border border-rose-500/20'
                  }`}
                >
                  <TrendIcon className="w-2.5 h-2.5 mr-0.5" />
                  {item.change}
                </span>
                <span className="text-slate-700/60 ml-2">•</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
