import React, { useState } from 'react';
import { ArrowLeftRight, Check, Zap } from 'lucide-react';

interface QuickSizingConverterProps {
  defaultPrice?: number;
  symbol?: string;
}

export const QuickSizingConverter: React.FC<QuickSizingConverterProps> = ({
  defaultPrice = 2940.0,
  symbol = 'RELIANCE',
}) => {
  const [capital, setCapital] = useState<number>(50000);
  const [selectedStock, setSelectedStock] = useState<string>(symbol);
  const [executed, setExecuted] = useState<boolean>(false);

  const priceMap: Record<string, number> = {
    RELIANCE: 2940.0,
    TCS: 4180.5,
    INFY: 1895.0,
    HDFCBANK: 1675.2,
    ICICIBANK: 1220.4,
  };

  const currentPrice = priceMap[selectedStock] || defaultPrice;
  const sharesCount = Math.floor(capital / currentPrice);
  const totalAllocated = sharesCount * currentPrice;
  const unallocated = capital - totalAllocated;

  const handleSimulate = () => {
    setExecuted(true);
    setTimeout(() => setExecuted(false), 2500);
  };

  return (
    <div className="glass-card p-6 relative overflow-hidden flex flex-col justify-between">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center">
            <Zap className="w-4 h-4 text-winsor-400 mr-1.5" />
            Capital-to-Shares Converter
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Instant tactical lot sizing with liquidity checks
          </p>
        </div>
        <select
          value={selectedStock}
          onChange={(e) => setSelectedStock(e.target.value)}
          className="px-2.5 py-1 rounded-xl bg-[#090b14] border border-white/[0.08] text-xs font-mono font-bold text-winsor-400 focus:outline-none focus:border-winsor-500/50"
        >
          <option value="RELIANCE">RELIANCE (₹2,940)</option>
          <option value="TCS">TCS (₹4,180)</option>
          <option value="INFY">INFY (₹1,895)</option>
          <option value="HDFCBANK">HDFCBANK (₹1,675)</option>
          <option value="ICICIBANK">ICICIBANK (₹1,220)</option>
        </select>
      </div>

      {/* Converter Dual Boxes with Center Swap Badge */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 items-center my-2">
        {/* Left: INR Capital Input */}
        <div className="sm:col-span-2 bg-[#080a12] p-3.5 rounded-2xl border border-white/[0.06] flex flex-col justify-between">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            INR Capital (₹500 – ₹10L)
          </span>
          <div className="flex items-baseline space-x-1 mt-1.5">
            <span className="text-slate-400 font-mono text-sm">₹</span>
            <input
              type="number"
              min={500}
              max={1000000}
              value={capital}
              onChange={(e) => setCapital(Math.max(500, Math.min(1000000, Number(e.target.value))))}
              step="500"
              className="bg-transparent font-mono font-extrabold text-xl text-white w-full focus:outline-none"
            />
          </div>
        </div>

        {/* Center Swap Action */}
        <div className="flex justify-center items-center">
          <div className="w-10 h-10 rounded-full bg-winsor-600/20 border border-winsor-500/40 flex items-center justify-center text-winsor-400 shadow-[0_0_15px_rgba(37,99,235,0.3)]">
            <ArrowLeftRight className="w-4 h-4 text-sky-400" />
          </div>
        </div>

        {/* Right: Calculated Shares Output */}
        <div className="sm:col-span-2 bg-[#080a12] p-3.5 rounded-2xl border border-white/[0.06] flex flex-col justify-between">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Optimal Lot
          </span>
          <div className="flex items-baseline justify-between mt-1.5">
            <span className={`font-mono font-extrabold text-xl ${sharesCount === 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {sharesCount}{' '}
              <span className="text-xs font-sans font-semibold text-slate-400">Shares</span>
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              ₹{totalAllocated.toLocaleString('en-IN')}
            </span>
          </div>
        </div>
      </div>

      {/* Quick Amount Chips */}
      <div className="flex flex-wrap items-center gap-1.5 py-2">
        <span className="text-[10px] font-mono text-slate-500 mr-1">Quick Presets:</span>
        {[500, 2000, 10000, 50000, 100000, 500000, 1000000].map((amt) => (
          <button
            key={amt}
            onClick={() => setCapital(amt)}
            className={`px-2 py-0.5 rounded-lg text-[11px] font-mono font-bold transition-all ${
              capital === amt
                ? 'bg-sky-500/20 text-sky-300 border border-sky-400/50 shadow-sm'
                : 'bg-[#080a12] text-slate-400 hover:text-white border border-white/[0.06]'
            }`}
          >
            {amt >= 100000 ? `₹${amt / 100000}L` : amt >= 1000 ? `₹${amt / 1000}k` : `₹${amt}`}
          </button>
        ))}
      </div>

      {sharesCount === 0 && (
        <div className="text-[11px] font-mono text-amber-300/90 py-1 flex items-center justify-between">
          <span>Capital &lt; 1 Share LTP (₹{currentPrice.toLocaleString('en-IN')})</span>
          <span>Shortfall: ₹{(currentPrice - capital).toLocaleString('en-IN')}</span>
        </div>
      )}

      {/* Sizing Details & Order Simulator Button */}
      <div className="mt-2 pt-3 border-t border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="text-[11px] text-slate-400 font-mono">
          Cash buffer remaining: <strong className="text-slate-200">₹{unallocated.toLocaleString('en-IN')}</strong> •
          Est. STT/Txn: <span className="text-winsor-400 font-semibold">₹18.50</span>
        </div>

        <button
          onClick={handleSimulate}
          className={`px-4 py-2 rounded-xl font-bold text-xs flex items-center justify-center space-x-1.5 transition-all ${
            executed
              ? 'bg-emerald-600 text-white shadow-[0_0_15px_rgba(16,185,129,0.5)]'
              : 'bg-gradient-to-r from-winsor-700 via-winsor-600 to-sky-500 hover:brightness-110 text-white shadow-[0_0_18px_rgba(37,99,235,0.4)]'
          }`}
        >
          {executed ? (
            <>
              <Check className="w-3.5 h-3.5 mr-1 text-white" />
              <span>Order Sized & Simulated!</span>
            </>
          ) : (
            <>
              <Zap className="w-3.5 h-3.5 mr-1" />
              <span>Simulate Market Execution</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
