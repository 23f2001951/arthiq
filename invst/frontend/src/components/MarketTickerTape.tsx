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
    <div className="w-full bg-[#06070a] border-y border-white/[0.06] overflow-hidden ticker-tape-container py-2 text-xs select-none">
      <div className="flex items-center">
        {/* Static live badge */}
        <div className="flex items-center space-x-1.5 px-3 py-0.5 bg-winsor-950 border-r border-winsor-800/40 text-winsor-400 font-semibold tracking-wider text-[10px] shrink-0 z-10 shadow-lg">
          <Radio className="w-3 h-3 text-winsor-400 animate-pulse" />
          <span>NSE LIVE</span>
        </div>

        {/* Scrolling marquee */}
        <div className="flex space-x-8 animate-marquee whitespace-nowrap pl-6">
          {tapeItems.map((item, idx) => {
            const TrendIcon = item.isPositive ? TrendingUp : TrendingDown;
            return (
              <div key={idx} className="inline-flex items-center space-x-2 font-mono">
                <span className="text-slate-300 font-semibold">{item.symbol}</span>
                <span className="text-slate-100">{item.price}</span>
                <span
                  className={`inline-flex items-center px-1.5 py-0.2 rounded text-[11px] font-medium ${
                    item.isPositive
                      ? 'text-emerald-400 bg-emerald-950/40'
                      : 'text-rose-400 bg-rose-950/40'
                  }`}
                >
                  <TrendIcon className="w-3 h-3 mr-0.5" />
                  {item.change}
                </span>
                <span className="text-slate-700">|</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
