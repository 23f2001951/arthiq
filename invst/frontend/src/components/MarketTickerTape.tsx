import React from 'react';
import { TrendingUp, TrendingDown, Radio } from 'lucide-react';

interface TickerItem {
  symbol: string;
  price: string;
  change: string;
  isPositive: boolean;
}

const TICKERS: TickerItem[] = [
  { symbol: 'NIFTY 50', price: '24,835.40', change: '+0.48%', isPositive: true },
  { symbol: 'SENSEX', price: '81,382.10', change: '+0.52%', isPositive: true },
  { symbol: 'BANK NIFTY', price: '51,240.85', change: '+0.31%', isPositive: true },
  { symbol: 'INDIA VIX', price: '12.84', change: '-3.12%', isPositive: false },
  { symbol: 'RELIANCE', price: '₹2,940.00', change: '+1.24%', isPositive: true },
  { symbol: 'TCS', price: '₹4,180.50', change: '+0.85%', isPositive: true },
  { symbol: 'HDFCBANK', price: '₹1,675.20', change: '-0.42%', isPositive: false },
  { symbol: 'INFY', price: '₹1,895.00', change: '+1.90%', isPositive: true },
  { symbol: 'ICICIBANK', price: '₹1,220.40', change: '+0.60%', isPositive: true },
  { symbol: 'USD/INR', price: '83.52', change: '+0.04%', isPositive: true },
  { symbol: 'BRENT CRUDE', price: '$78.40', change: '-1.15%', isPositive: false },
  { symbol: '10Y G-SEC', price: '6.84%', change: '-0.02%', isPositive: false },
];

export const MarketTickerTape: React.FC = () => {
  // Duplicate array to enable seamless marquee looping
  const tapeItems = [...TICKERS, ...TICKERS];

  return (
    <div className="relative w-full bg-[#05070c]/90 backdrop-blur-md border-y border-white/[0.06] overflow-hidden ticker-tape-container py-2 text-xs select-none">
      {/* Edge gradient fade masks for seamless floating appearance */}
      <div className="pointer-events-none absolute left-24 top-0 bottom-0 w-12 bg-gradient-to-r from-[#05070c] to-transparent z-10" />
      <div className="pointer-events-none absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-[#05070c] to-transparent z-10" />

      <div className="flex items-center">
        {/* Static live badge with pulsing radar beacon */}
        <div className="relative flex items-center space-x-1.5 px-3 py-1 bg-gradient-to-r from-winsor-950 to-slate-950 border-r border-winsor-800/40 text-winsor-400 font-bold tracking-wider text-[10px] shrink-0 z-20 shadow-[4px_0_12px_rgba(0,0,0,0.5)]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <Radio className="w-3 h-3 text-sky-400" />
          <span className="font-mono">NSE LIVE</span>
        </div>

        {/* Scrolling marquee */}
        <div className="flex space-x-6 animate-marquee whitespace-nowrap pl-6">
          {tapeItems.map((item, idx) => {
            const TrendIcon = item.isPositive ? TrendingUp : TrendingDown;
            return (
              <div
                key={idx}
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
