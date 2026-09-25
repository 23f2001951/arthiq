import React from 'react';
import { ArrowRight, ShieldCheck, Play, Sparkles } from 'lucide-react';

interface HeroClarityBannerProps {
  onExploreTools: () => void;
  onLaunchBacktest: () => void;
}

export const HeroClarityBanner: React.FC<HeroClarityBannerProps> = ({
  onExploreTools,
  onLaunchBacktest,
}) => {
  return (
    <div className="relative overflow-hidden rounded-3xl bg-[#080a11] border border-white/[0.08] p-8 sm:p-12 text-center flex flex-col items-center justify-center shadow-2xl">
      {/* Subtle radial ambient illumination */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-56 bg-gradient-to-b from-amber-500/20 via-sky-500/10 to-transparent blur-3xl pointer-events-none animate-pulse-subtle" />
      <div className="absolute inset-0 bg-dot-grid opacity-25 pointer-events-none" />

      {/* Official Arth_IQ Logo Placement with Floating Animation & Halo */}
      <div className="mb-4 relative group animate-float">
        <div className="absolute -inset-2 bg-gradient-to-r from-amber-500/30 via-yellow-400/20 to-sky-500/30 rounded-3xl blur-xl opacity-75 group-hover:opacity-100 transition-opacity" />
        <div className="relative w-16 h-16 sm:w-20 sm:h-20 rounded-2xl p-1.5 bg-gradient-to-tr from-[#121624] via-[#0b0e18] to-[#06080e] border border-amber-400/50 shadow-[0_0_35px_rgba(234,179,8,0.3)] flex items-center justify-center backdrop-blur-xl group-hover:border-amber-300 transition-all">
          <img
            src="/Arth_IQ.png"
            alt="Arth IQ"
            className="w-full h-full object-contain rounded-xl drop-shadow-md"
          />
        </div>
      </div>

      {/* Four Core Pillars: RESEARCH | ANALYSE | INVEST | GROW */}
      <div className="flex items-center space-x-2 text-[10px] sm:text-xs font-mono font-bold text-amber-300/90 tracking-widest uppercase mb-4">
        <span className="hover:text-amber-200 transition-colors">Research</span>
        <span className="text-amber-500/50">•</span>
        <span className="hover:text-amber-200 transition-colors">Analyse</span>
        <span className="text-amber-500/50">•</span>
        <span className="hover:text-amber-200 transition-colors">Invest</span>
        <span className="text-amber-500/50">•</span>
        <span className="hover:text-amber-200 transition-colors">Grow</span>
      </div>

      {/* Top Tag Pill */}
      <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs font-semibold text-slate-300 mb-6 backdrop-blur-md hover:border-white/[0.16] transition-colors">
        <Sparkles className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
        <span>Arth IQ Personal Investment Intelligence</span>
        <span className="w-1 h-1 rounded-full bg-slate-500" />
        <span className="text-emerald-400 flex items-center font-mono text-[11px] font-bold">
          <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
          Zero-Lookahead Point-in-Time
        </span>
      </div>

      {/* Main Headline */}
      <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight max-w-3xl leading-[1.15]">
        See The Market <br className="hidden sm:block" />
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-amber-100 to-amber-300">
          With Clarity.
        </span>
      </h1>

      {/* Subtitle */}
      <p className="mt-4 text-xs sm:text-sm text-slate-400 max-w-xl leading-relaxed">
        Our multi-factor quantitative engine transforms complex NSE data into transparent,
        rule-based alpha across Quality, Valuation, Risk, and Sentiment overlays.
      </p>

      {/* CTA Button Group */}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={onExploreTools}
          className="relative px-6 py-3 rounded-full bg-gradient-to-r from-[#171a26] via-[#11131c] to-[#0f1118] text-white text-xs sm:text-sm font-bold btn-glow-amber flex items-center space-x-2 hover:scale-[1.03] active:scale-[0.97] transition-all cursor-pointer shadow-lg shimmer-mask"
        >
          <span>Explore Stock Ideas & Quick Picks</span>
          <ArrowRight className="w-4 h-4 text-amber-400" />
        </button>

        <button
          onClick={onLaunchBacktest}
          className="px-5 py-3 rounded-full bg-white/[0.04] hover:bg-white/[0.09] border border-white/[0.08] hover:border-sky-400/40 text-slate-300 hover:text-white text-xs sm:text-sm font-semibold flex items-center space-x-2 hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer"
        >
          <Play className="w-3.5 h-3.5 text-sky-400 fill-sky-400" />
          <span>Launch Backtest Lab</span>
        </button>
      </div>
    </div>
  );
};
