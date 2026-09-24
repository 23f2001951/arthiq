import React, { useState } from 'react';
import { Search, Plus, ArrowUpRight, ArrowDownLeft, Sparkles, Filter } from 'lucide-react';

interface TransactionItem {
  id: string;
  symbol: string;
  name: string;
  avatarColor: string;
  type: 'BUY' | 'SELL' | 'DIVIDEND' | 'REBALANCE';
  amount: number;
  date: string;
  shares: number;
}

const TRANSACTIONS: TransactionItem[] = [
  {
    id: 'tx-1',
    symbol: 'RELIANCE',
    name: 'Reliance Industries Ltd',
    avatarColor: 'from-blue-600 to-indigo-700',
    type: 'BUY',
    amount: 147000,
    shares: 50,
    date: 'Today, 10:30 AM',
  },
  {
    id: 'tx-2',
    symbol: 'TCS',
    name: 'Tata Consultancy Services',
    avatarColor: 'from-cyan-600 to-blue-700',
    type: 'BUY',
    amount: 104500,
    shares: 25,
    date: 'Yesterday, 02:15 PM',
  },
  {
    id: 'tx-3',
    symbol: 'INFY',
    name: 'Infosys Limited',
    avatarColor: 'from-purple-600 to-indigo-700',
    type: 'DIVIDEND',
    amount: 3200,
    shares: 80,
    date: 'Sep 18, 11:00 AM',
  },
  {
    id: 'tx-4',
    symbol: 'HDFCBANK',
    name: 'HDFC Bank Ltd',
    avatarColor: 'from-blue-700 to-slate-800',
    type: 'REBALANCE',
    amount: 41875,
    shares: 25,
    date: 'Sep 15, 03:20 PM',
  },
  {
    id: 'tx-5',
    symbol: 'LT',
    name: 'Larsen & Toubro Ltd',
    avatarColor: 'from-amber-600 to-orange-700',
    type: 'SELL',
    amount: 72400,
    shares: 20,
    date: 'Sep 12, 09:45 AM',
  },
];

export const TradeOrderBlotter: React.FC = () => {
  const [query, setQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('ALL');

  const filtered = TRANSACTIONS.filter((tx) => {
    const matchesQuery =
      tx.symbol.toLowerCase().includes(query.toLowerCase()) ||
      tx.name.toLowerCase().includes(query.toLowerCase());
    const matchesType = filterType === 'ALL' || tx.type === filterType;
    return matchesQuery && matchesType;
  });

  return (
    <div className="glass-card p-6 relative overflow-hidden flex flex-col justify-between">
      {/* Header with Search & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <div>
          <h3 className="text-base font-bold text-white flex items-center">
            <Sparkles className="w-4 h-4 text-winsor-400 mr-2" />
            Execution Blotter & Orders
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time portfolio order executions and dividend allocations
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {/* Search box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search ticker..."
              className="pl-8 pr-3 py-1.5 rounded-xl bg-[#080a11] border border-white/[0.08] text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-winsor-500/50 w-36 sm:w-48 transition-all"
            />
          </div>

          {/* Quick Filter toggle */}
          <button
            onClick={() =>
              setFilterType(
                filterType === 'ALL'
                  ? 'BUY'
                  : filterType === 'BUY'
                  ? 'SELL'
                  : 'ALL'
              )
            }
            className="p-1.5 rounded-xl bg-[#080a11] border border-white/[0.08] text-slate-400 hover:text-white hover:border-winsor-500/40 transition-colors"
            title="Filter type"
          >
            <Filter className="w-3.5 h-3.5" />
          </button>

          {/* New Execution Action */}
          <button className="p-1.5 rounded-xl bg-winsor-600 hover:bg-winsor-500 text-white shadow-[0_0_10px_rgba(37,99,235,0.5)] transition-all">
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Orders List */}
      <div className="space-y-3">
        {filtered.map((tx) => {
          const isCredit = tx.type === 'DIVIDEND' || tx.type === 'SELL';
          return (
            <div
              key={tx.id}
              className="flex items-center justify-between p-3 rounded-xl bg-[#080b12]/80 border border-white/[0.04] hover:border-winsor-500/30 hover:bg-[#0c101c] transition-all group"
            >
              {/* Left: Avatar & Symbol */}
              <div className="flex items-center space-x-3">
                <div
                  className={`w-9 h-9 rounded-full bg-gradient-to-tr ${tx.avatarColor} flex items-center justify-center text-white font-mono text-xs font-bold shadow-md shadow-black/50 group-hover:scale-105 transition-transform`}
                >
                  {tx.symbol.slice(0, 2)}
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-xs text-white">
                      {tx.symbol}
                    </span>
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        tx.type === 'BUY'
                          ? 'bg-winsor-950 text-winsor-400 border border-winsor-800/50'
                          : tx.type === 'DIVIDEND'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                          : tx.type === 'SELL'
                          ? 'bg-rose-950 text-rose-400 border border-rose-800/50'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {tx.type}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">{tx.name}</p>
                </div>
              </div>

              {/* Right: Amount & Date */}
              <div className="text-right">
                <div
                  className={`font-mono text-xs font-bold flex items-center justify-end ${
                    isCredit ? 'text-emerald-400' : 'text-slate-200'
                  }`}
                >
                  {isCredit ? (
                    <ArrowDownLeft className="w-3 h-3 mr-0.5 text-emerald-400" />
                  ) : (
                    <ArrowUpRight className="w-3 h-3 mr-0.5 text-slate-400" />
                  )}
                  {isCredit ? '+' : '-'}₹{tx.amount.toLocaleString('en-IN')}
                </div>
                <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                  {tx.shares} shares • {tx.date}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
