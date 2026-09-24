import React from 'react';
import {
  Sparkles,
  Eye,
  Radio,
} from 'lucide-react';

export type StockIdeasSubTab = 'alpha_picks' | 'lens' | 'radar';

interface StockIdeasSubNavProps {
  activeSubTab: StockIdeasSubTab;
  onSelectSubTab: (subTab: StockIdeasSubTab) => void;
}

interface SubNavTabConfig {
  id: StockIdeasSubTab;
  label: string;
  badge: string;
  icon: React.ComponentType<{ className?: string }>;
  activeClasses: string;
  iconColor: string;
  dotColor: string;
}

const SUB_TABS: SubNavTabConfig[] = [
  {
    id: 'alpha_picks',
    label: 'Alpha Picks & Ideas',
    badge: 'MULTI-FACTOR',
    icon: Sparkles,
    activeClasses: 'bg-gradient-to-r from-winsor-700 to-sky-600 text-white border-sky-400/40 shadow-[0_0_15px_rgba(37,99,235,0.4)]',
    iconColor: 'text-sky-400',
    dotColor: 'bg-sky-400',
  },
  {
    id: 'lens',
    label: 'Factor Screener',
    badge: 'DEEP DIVE',
    icon: Eye,
    activeClasses: 'bg-gradient-to-r from-amber-700 to-yellow-600 text-white border-amber-400/50 shadow-[0_0_15px_rgba(245,158,11,0.35)]',
    iconColor: 'text-amber-400',
    dotColor: 'bg-amber-400',
  },
  {
    id: 'radar',
    label: 'Signals & Thematic Radar',
    badge: 'REAL-TIME',
    icon: Radio,
    activeClasses: 'bg-gradient-to-r from-purple-700 to-indigo-600 text-white border-purple-400/50 shadow-[0_0_15px_rgba(147,51,234,0.35)]',
    iconColor: 'text-purple-400',
    dotColor: 'bg-purple-400',
  },
];

export const StockIdeasSubNav: React.FC<StockIdeasSubNavProps> = ({
  activeSubTab,
  onSelectSubTab,
}) => {
  return (
    <div className="w-full bg-[#070912]/95 backdrop-blur-xl border-b border-white/[0.08] py-2.5 px-4 sm:px-6 lg:px-8 select-none transition-all sticky top-16 z-20 shadow-md">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3 overflow-x-auto no-scrollbar">
        {/* Left: Quick Context Tag */}
        <div className="hidden sm:flex items-center space-x-2 mr-2 pr-3 border-r border-white/[0.08] shrink-0">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">
            Module
          </span>
        </div>

        {/* The 3 Streamlined Sub-Nav Tabs */}
        <div className="flex items-center space-x-2 shrink-0">
          {SUB_TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeSubTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onSelectSubTab(tab.id)}
                className={`group relative flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold border transition-all duration-200 cursor-pointer ${
                  isActive
                    ? tab.activeClasses
                    : 'bg-[#0b0e18] border-white/[0.06] text-slate-400 hover:text-slate-100 hover:bg-[#121624] hover:border-white/[0.12]'
                }`}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 transition-transform group-hover:scale-110 ${
                    isActive ? 'text-white' : tab.iconColor
                  }`}
                />
                <span className="whitespace-nowrap tracking-tight">{tab.label}</span>
                <span
                  className={`hidden md:inline-block text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full uppercase transition-colors ${
                    isActive
                      ? 'bg-black/30 text-white/90'
                      : 'bg-white/[0.03] text-slate-500 group-hover:text-slate-400'
                  }`}
                >
                  {tab.badge}
                </span>
                {isActive && (
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${tab.dotColor} shadow-[0_0_8px_currentColor] ml-1`}
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* Right Status / Context Badge */}
        <div className="hidden lg:flex items-center space-x-2 pl-3 border-l border-white/[0.08] text-[10px] font-mono text-slate-400 shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>NSE 500 Dynamic Universe</span>
        </div>
      </div>
    </div>
  );
};
