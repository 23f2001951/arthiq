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
    <div className="relative overflow-hidden rounded-3xl bg-[#090b12] border border-white/[0.08] p-8 sm:p-12 text-center flex flex-col items-center justify-center">
      {/* Subtle radial ambient illumination */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-48 bg-gradient-to-b from-amber-500/15 via-winsor-500/5 to-transparent blur-3xl pointer-events-none" />
      <div className="absolute inset-0 bg-dot-grid opacity-25 pointer-events-none" />

      {/* Official Arth_IQ Logo Placement */}
      <div className="mb-4 relative group">
        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl p-1 bg-gradient-to-tr from-amber-500/40 via-yellow-400/20 to-transparent border border-amber-400/40 shadow-[0_0_35px_rgba(234,179,8,0.25)] flex items-center justify-center backdrop-blur-xl">
          <img
            src="/Arth_IQ.png"
            alt="Arth IQ"
            className="w-full h-full object-contain rounded-xl"
          />
        </div>
      </div>

      {/* Four Core Pillars: RESEARCH | ANALYSE | INVEST | GROW */}
      <div className="flex items-center space-x-2 text-[10px] sm:text-xs font-mono font-bold text-amber-300/90 tracking-widest uppercase mb-4">
        <span>Research</span>
        <span className="text-amber-500/50">•</span>
        <span>Analyse</span>
        <span className="text-amber-500/50">•</span>
        <span>Invest</span>
        <span className="text-amber-500/50">•</span>
        <span>Grow</span>
      </div>

      {/* Top Tag Pill */}
      <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs font-semibold text-slate-300 mb-6 backdrop-blur-md">
        <Sparkles className="w-3.5 h-3.5 text-amber-400" />
        <span>Arth IQ Personal Investment Intelligence</span>
        <span className="w-1 h-1 rounded-full bg-slate-500" />
        <span className="text-emerald-400 flex items-center font-mono text-[11px]">
          <ShieldCheck className="w-3 h-3 mr-1" />
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
          className="px-6 py-3 rounded-full bg-[#11131c] text-white text-xs sm:text-sm font-bold btn-glow-amber flex items-center space-x-2 transition-all cursor-pointer"
        >
          <span>Explore Stock Ideas & Quick Picks</span>
          <ArrowRight className="w-4 h-4 text-amber-400" />
        </button>

        <button
          onClick={onLaunchBacktest}
          className="px-5 py-3 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 text-xs sm:text-sm font-semibold flex items-center space-x-2 transition-all cursor-pointer"
        >
          <Play className="w-3.5 h-3.5 text-sky-400 fill-sky-400" />
          <span>Launch Backtest Lab</span>
        </button>
      </div>
    </div>
  );
};
