import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const ModernArtboxFooter: React.FC = () => {
  return (
    <footer className="mt-12 rounded-3xl bg-[#080a11] border border-white/[0.06] p-6 sm:p-8 relative overflow-hidden">
      <div className="absolute inset-0 bg-dot-grid opacity-10 pointer-events-none" />

      <div className="flex flex-col md:flex-row items-center justify-between gap-6 relative z-10">
        {/* Left: Logo & Motto */}
        <div className="flex items-center space-x-3.5">
          <img
            src="/Arth_IQ.png"
            alt="Arth IQ"
            className="w-12 h-12 rounded-xl object-contain bg-black/60 border border-amber-500/30 shadow-md shrink-0"
          />
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-black text-xl text-white tracking-tight">
                ARTH <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-200">IQ</span>
              </span>
              <span className="text-[9px] font-mono font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20">
                PERSONAL INVESTMENT INTELLIGENCE
              </span>
            </div>
            <p className="text-[10px] text-amber-300/70 font-mono tracking-wider uppercase mt-1">
              Discipline Creates Freedom • Compound A Brighter Tomorrow
            </p>
          </div>
        </div>

        {/* Right: Verification & Social Badges */}
        <div className="flex flex-col sm:flex-row items-center sm:items-end md:items-center space-y-2 sm:space-y-0 sm:space-x-4 text-[11px] text-slate-400">
          <div className="flex items-center space-x-1.5 text-emerald-400 font-mono text-xs">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Point-in-Time Audit Certified</span>
          </div>

          <span className="hidden sm:inline text-slate-700">|</span>

          {/* Social Pill Badges */}
          <div className="flex items-center space-x-2">
            <span className="w-7 h-7 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] flex items-center justify-center text-slate-400 hover:text-white cursor-pointer transition-colors font-bold text-xs">
              𝕏
            </span>
            <span className="w-7 h-7 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] flex items-center justify-center text-slate-400 hover:text-white cursor-pointer transition-colors font-bold text-xs">
              in
            </span>
            <span className="w-7 h-7 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] flex items-center justify-center text-slate-400 hover:text-white cursor-pointer transition-colors font-bold text-xs">
              ⌘
            </span>
          </div>
        </div>
      </div>

      {/* Subtle bottom copyright line */}
      <div className="mt-6 pt-4 border-t border-white/[0.04] flex flex-col sm:flex-row items-center justify-between text-[10px] text-slate-500 font-mono gap-2 relative z-10">
        <span>RESEARCH • ANALYSE • INVEST • GROW</span>
        <span>Not financial advice. Quantitative decision support engine for NSE equities. @ArthIQ.</span>
      </div>
    </footer>
  );
};
