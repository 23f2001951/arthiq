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
  const accentGradients: Record<string, string> = {
    winsor: 'from-transparent via-winsor-500/70 to-transparent',
    info: 'from-transparent via-sky-400/70 to-transparent',
    emerald: 'from-transparent via-emerald-500/70 to-transparent',
    success: 'from-transparent via-emerald-500/70 to-transparent',
    amber: 'from-transparent via-amber-500/70 to-transparent',
    warning: 'from-transparent via-amber-500/70 to-transparent',
    purple: 'from-transparent via-purple-500/70 to-transparent',
    default: 'from-transparent via-white/20 to-transparent',
  };

  const accentLine = accentGradients[variant] || accentGradients.winsor;

  return (
    <div className="glass-card p-5 relative overflow-hidden group hover:scale-[1.01] transition-all duration-300">
      {/* Subtle top glow highlight */}
      <div className={`absolute top-0 left-0 right-0 h-[1.5px] bg-gradient-to-r ${accentLine}`} />

      {/* Header with Title and Coin/Token Badge */}
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-semibold text-slate-400 tracking-wide block">
            {label}
          </span>
          <div className="mt-2 flex items-baseline">
            <h3 className="text-2xl sm:text-3xl font-extrabold font-mono text-white tracking-tight">
              {value}
            </h3>
          </div>
        </div>

        {/* Circular Token Badge (inspired by reference image) */}
        <div className="w-8 h-8 rounded-full bg-[#121624] border border-white/10 flex items-center justify-center text-slate-300 shadow-inner group-hover:border-winsor-400/50 group-hover:text-winsor-400 transition-colors">
          {Icon ? (
            <Icon className="w-4 h-4" />
          ) : (
            <span className="font-mono text-xs font-bold text-winsor-400">₹</span>
          )}
        </div>
      </div>

      {/* Bottom Subtitle, Delta, and Sparkline */}
      <div className="mt-4 flex items-center justify-between pt-2 border-t border-white/[0.04]">
        {subtitle && (
          <span className="text-xs text-slate-400 truncate max-w-[140px]">
            {subtitle}
          </span>
        )}

        {delta && (
          <div
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono font-bold ${
              deltaPositive
                ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-800/40'
                : 'text-rose-400 bg-rose-950/40 border border-rose-800/40'
            }`}
          >
            {deltaPositive ? (
              <TrendingUp className="w-3 h-3 mr-1" />
            ) : (
              <TrendingDown className="w-3 h-3 mr-1" />
            )}
            {delta}
          </div>
        )}

        {sparkline && (
          <div className="ml-auto">
            <TrendSparkline
              color={deltaPositive && trendPositive ? 'emerald' : 'cyan'}
              isPositive={deltaPositive && trendPositive}
              width={70}
              height={20}
            />
          </div>
        )}
      </div>
    </div>
  );
};
