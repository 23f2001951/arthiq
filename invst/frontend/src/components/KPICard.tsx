import React from 'react';
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react';
import { TrendSparkline } from './TrendSparkline';

export type KPIVariant =
  | 'default'
  | 'winsor'
  | 'emerald'
  | 'amber'
  | 'purple'
  | 'success'
  | 'warning'
  | 'info';

interface KPICardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  delta?: string;
  deltaPositive?: boolean;
  icon?: LucideIcon;
  variant?: KPIVariant;
  sparkline?: boolean;
  trendPositive?: boolean;
}

export const KPICard: React.FC<KPICardProps> = ({
  label,
  value,
  subtitle,
  delta,
  deltaPositive = true,
  icon: Icon,
  variant = 'winsor',
  sparkline = false,
  trendPositive = true,
}) => {
  const accentGradients: Record<string, { line: string; glow: string }> = {
    winsor: { line: 'from-transparent via-sky-400 to-transparent', glow: 'bg-sky-500/5' },
    info: { line: 'from-transparent via-cyan-400 to-transparent', glow: 'bg-cyan-500/5' },
    emerald: { line: 'from-transparent via-emerald-400 to-transparent', glow: 'bg-emerald-500/5' },
    success: { line: 'from-transparent via-emerald-400 to-transparent', glow: 'bg-emerald-500/5' },
    amber: { line: 'from-transparent via-amber-400 to-transparent', glow: 'bg-amber-500/5' },
    warning: { line: 'from-transparent via-amber-400 to-transparent', glow: 'bg-amber-500/5' },
    purple: { line: 'from-transparent via-purple-400 to-transparent', glow: 'bg-purple-500/5' },
    default: { line: 'from-transparent via-white/30 to-transparent', glow: 'bg-white/5' },
  };

  const style = accentGradients[variant] || accentGradients.winsor;

  return (
    <div className="glass-panel p-5 relative overflow-hidden group hover:-translate-y-1.5 hover:scale-[1.015] hover:border-white/[0.16] hover:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.9),0_0_20px_rgba(56,189,248,0.12)] transition-all duration-300 select-none">
      {/* Subtle top glow highlight line */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r ${style.line}`} />
      <div className={`absolute top-0 right-0 w-36 h-36 ${style.glow} blur-3xl pointer-events-none group-hover:scale-125 transition-transform duration-500`} />

      {/* Header with Title and Coin/Token Badge */}
      <div className="flex items-start justify-between relative z-10">
        <div>
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block font-mono">
            {label}
          </span>
          <div className="mt-2 flex items-baseline">
            <h3 className="text-2xl sm:text-3xl font-black font-mono text-white tracking-tight drop-shadow-sm">
              {value}
            </h3>
          </div>
        </div>

        {/* Circular Token Badge */}
        <div className="w-9 h-9 rounded-2xl bg-[#0b0f1c] border border-white/[0.08] flex items-center justify-center text-slate-300 shadow-inner group-hover:border-sky-400/50 group-hover:text-sky-300 group-hover:shadow-[0_0_12px_rgba(56,189,248,0.3)] transition-all">
          {Icon ? (
            <Icon className="w-4 h-4" />
          ) : (
            <span className="font-mono text-xs font-bold text-sky-400">₹</span>
          )}
        </div>
      </div>

      {/* Bottom Subtitle, Delta, and Sparkline */}
      <div className="mt-4 flex items-center justify-between pt-3 border-t border-white/[0.06] relative z-10">
        {subtitle && (
          <span className="text-[11px] text-slate-400 truncate max-w-[140px] font-medium">
            {subtitle}
          </span>
        )}

        {delta && (
          <div
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${
              deltaPositive
                ? 'text-emerald-300 bg-emerald-950/60 border border-emerald-500/30'
                : 'text-rose-300 bg-rose-950/60 border border-rose-500/30'
            }`}
          >
            {deltaPositive ? (
              <TrendingUp className="w-3 h-3 mr-1 text-emerald-400" />
            ) : (
              <TrendingDown className="w-3 h-3 mr-1 text-rose-400" />
            )}
            {delta}
          </div>
        )}

        {sparkline && (
          <div className="ml-auto pl-2">
            <TrendSparkline
              color={deltaPositive && trendPositive ? 'emerald' : 'cyan'}
              isPositive={deltaPositive && trendPositive}
              width={75}
              height={22}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default KPICard;
