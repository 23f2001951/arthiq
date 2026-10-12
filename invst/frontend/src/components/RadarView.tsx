import React, { useState } from 'react';
import { PulseView } from './PulseView';
import { EdgeView } from './EdgeView';
import { StockRecommendationItem } from '../types/api';
import { BarChart3, Radio } from 'lucide-react';

interface RadarViewProps {
  recommendations: StockRecommendationItem[];
  asof: string;
}

export const RadarView: React.FC<RadarViewProps> = ({ recommendations, asof }) => {
  const [subMode, setSubMode] = useState<'signals' | 'themes'>('signals');

  return (
    <div className="space-y-6">
      {/* Sub-mode switcher pill */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-[#080b13] border border-white/[0.08] shadow-lg">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Market Radar &amp; Signal Engine
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Point-in-time disclosures and rankings from the selected model run
            </p>
          </div>
        </div>

        <div className="flex items-center p-1 bg-[#04060b] border border-white/[0.06] rounded-xl">
          <button
            onClick={() => setSubMode('signals')}
            className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              subMode === 'signals'
                ? 'bg-gradient-to-r from-purple-700 to-indigo-600 text-white shadow-md border border-purple-400/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
                <Radio className="w-3.5 h-3.5" />
                <span>Corporate Events</span>
          </button>
          <button
            onClick={() => setSubMode('themes')}
            className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              subMode === 'themes'
                ? 'bg-gradient-to-r from-cyan-700 to-blue-600 text-white shadow-md border border-cyan-400/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Factor Leaders</span>
          </button>
        </div>
      </div>

      {/* Render selected view */}
      {subMode === 'signals' ? <EdgeView asof={asof} /> : <PulseView recommendations={recommendations} asof={asof} />}
    </div>
  );
};
