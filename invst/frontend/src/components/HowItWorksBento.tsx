import React from 'react';
import { Database, Sliders, Zap } from 'lucide-react';

export const HowItWorksBento: React.FC = () => {
  const steps = [
    {
      step: 'STEP 1',
      title: 'Ingest & Validate',
      description:
        'Point-in-time Bhavcopy, quarterly filings, and corporate disclosures strictly timestamped to eliminate lookahead bias.',
      icon: Database,
      halo: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
      pillColor: 'text-cyan-400 bg-cyan-950/40 border-cyan-800/40',
    },
    {
      step: 'STEP 2',
      title: 'Multi-Factor Scoring',
      description:
        'Ranks the universe through Stage 0 liquidity screens, Quality (ROE/ROCE), Valuation, Downside Risk, and Sentiment overlay.',
      icon: Sliders,
      halo: 'bg-winsor-500/10 text-winsor-400 border-winsor-500/30',
      pillColor: 'text-winsor-400 bg-winsor-950/40 border-winsor-800/40',
    },
    {
      step: 'STEP 3',
      title: 'Optimize & Execute',
      description:
        'Solves Markowitz risk parity weights, enforces 25% sector & stock caps, and sizes exact share lots for tactical deployment.',
      icon: Zap,
      halo: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      pillColor: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Section Header (Inspired by Image 4) */}
      <div className="text-center max-w-xl mx-auto">
        <h2 className="text-2xl sm:text-4xl font-black text-white tracking-tight">
          How Arth IQ Works
        </h2>
        <p className="mt-2 text-xs sm:text-sm text-slate-400">
          Institutional quantitative rigor simplified into 3 transparent, audit-certified stages.
        </p>
      </div>

      {/* 3 Bento Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {steps.map((s, idx) => {
          const Icon = s.icon;
          return (
            <div
              key={idx}
              className="glass-card p-6 sm:p-8 relative overflow-hidden bg-concentric-rings flex flex-col justify-between group hover:border-winsor-500/40 transition-all duration-300"
            >
              <div className="absolute inset-0 bg-dot-grid opacity-15 pointer-events-none" />

              <div>
                {/* Circular Icon with Soft Glow Halo */}
                <div
                  className={`w-12 h-12 rounded-2xl border flex items-center justify-center shadow-lg transition-transform group-hover:scale-105 ${s.halo}`}
                >
                  <Icon className="w-6 h-6" />
                </div>

                {/* Step Pill */}
                <div className="mt-6">
                  <span
                    className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border tracking-wider uppercase ${s.pillColor}`}
                  >
                    {s.step}
                  </span>
                </div>

                {/* Title */}
                <h3 className="text-lg font-bold text-white tracking-tight mt-3">
                  {s.title}
                </h3>

                {/* Description */}
                <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                  {s.description}
                </p>
              </div>

              {/* Bottom Subtle Index Marker */}
              <div className="mt-6 pt-3 border-t border-white/[0.04] flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>STAGE 0{idx + 1}</span>
                <span className="text-slate-400 group-hover:text-white transition-colors">
                  0{idx + 1}/03
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
