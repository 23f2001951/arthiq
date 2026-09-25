import React, { useState, useEffect } from 'react';
import {
  Menu,
  Clock,
  Calendar,
  Plus,
  ShieldCheck,
  Sparkles,
  Search,
  LayoutDashboard,
  Briefcase,
  Target,
  Sliders,
  Users,
  BrainCircuit,
} from 'lucide-react';
import { NavTab } from './Navbar';
import { getUserRole } from '../api/client';

interface TopHeaderProps {
  currentTab: NavTab;
  systemHealthy?: boolean;
  onQuickAction?: () => void;
  onOpenMobileSidebar?: () => void;
}

const TAB_TITLES: Record<NavTab, { title: string; subtitle: string; icon: React.ComponentType<{ className?: string }> }> = {
  // Investor Platform Tabs
  dashboard: {
    title: 'Executive Portfolio Dashboard',
    subtitle: 'Point-in-Time Indian Equities & Tactical Dip Allocation',
    icon: LayoutDashboard,
  },
  recommendations: {
    title: 'Stock Ideas & Alpha Picks',
    subtitle: 'Multi-factor quantitative conviction picks',
    icon: Sparkles,
  },
  analyzer: {
    title: 'Single Stock & ETF Analyzer',
    subtitle: 'Live returns, BQS vs investment score, and redlines',
    icon: Search,
  },
  portfolio: {
    title: 'My Portfolio Health',
    subtitle: 'Sector exposure, risk caps & tactical rebalancing',
    icon: Briefcase,
  },
  targetlist: {
    title: 'Tactical Target Lists & Wishlists',
    subtitle: 'Dip accumulation triggers, watchlist levels & entry zones',
    icon: Target,
  },
  // Admin Platform Tabs
  admin_dashboard: {
    title: 'Admin Command Center',
    subtitle: 'Platform telemetry, Pro Investor accounts, and ML model status',
    icon: LayoutDashboard,
  },
  users: {
    title: 'Pro Investor Management',
    subtitle: 'Provision and onboard institutional investors by email',
    icon: Users,
  },
  model_training: {
    title: 'Alpha Model Training & Calibration',
    subtitle: 'Point-in-Time LightGBM hyperparameters and feature sets',
    icon: BrainCircuit,
  },
  backtest: {
    title: 'Quantitative Backtest Engine',
    subtitle: 'Factor persistence & historical walk-forward simulation',
    icon: Sliders,
  },
  health: {
    title: 'System Health & PIT Audit',
    subtitle: 'Point-in-Time data integrity and service monitors',
    icon: ShieldCheck,
  },
};

export const TopHeader: React.FC<TopHeaderProps> = ({
  currentTab,
  systemHealthy: _systemHealthy,
  onQuickAction,
  onOpenMobileSidebar,
}) => {
  const [istDate, setIstDate] = useState('');
  const [istTime, setIstTime] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const dateFormatted = new Intl.DateTimeFormat('en-IN', {
        timeZone: 'Asia/Kolkata',
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }).format(now);

      const timeFormatted = new Intl.DateTimeFormat('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
      }).format(now);

      setIstDate(dateFormatted);
      setIstTime(timeFormatted);
    };

    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const meta = TAB_TITLES[currentTab] || TAB_TITLES.dashboard;
  const PageIcon = meta.icon;
  const role = getUserRole();

  return (
    <header className="sticky top-0 z-30 bg-[#06070a]/90 backdrop-blur-xl border-b border-white/[0.06] select-none">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left: Mobile Menu Trigger + Breadcrumb / Active Page Title */}
          <div className="flex items-center space-x-3">
            {onOpenMobileSidebar && (
              <button
                onClick={onOpenMobileSidebar}
                className="lg:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.05] transition-colors"
              >
                <Menu className="w-5 h-5" />
              </button>
            )}

            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-lg bg-winsor-900/40 border border-winsor-500/30 flex items-center justify-center text-sky-400 shrink-0">
                <PageIcon className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-sm sm:text-base font-bold text-white tracking-tight leading-none">
                    {meta.title}
                  </h1>
                </div>
                <p className="text-[10px] text-slate-400 font-mono tracking-wide leading-none mt-1 hidden sm:block">
                  {meta.subtitle}
                </p>
              </div>
            </div>
          </div>

          {/* Right: Actions + Live IST Clock */}
          <div className="flex items-center space-x-2.5 sm:space-x-3">

            {/* Tactical Order / Analyze CTA (Investor Only) */}
            {role === 'user' && onQuickAction && (
              <button
                onClick={onQuickAction}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-winsor-600 to-sky-500 hover:brightness-110 text-white text-xs font-bold shadow-[0_0_15px_rgba(37,99,235,0.35)] transition-all cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5 stroke-[3]" />
                <span className="hidden sm:inline">Tactical Order</span>
                <span className="sm:hidden">Order</span>
              </button>
            )}

            {/* Live IST Date & Clock (Clean Stacked Box) */}
            <div className="hidden sm:flex flex-col items-end justify-center px-3 py-1 rounded-xl bg-[#080b13] border border-white/[0.08] shadow-inner font-mono">
              <div className="flex items-center space-x-1 text-[11px] font-semibold text-slate-300 leading-tight">
                <Calendar className="w-3 h-3 text-sky-400" />
                <span>{istDate}</span>
              </div>
              <div className="flex items-center space-x-1 text-[11px] font-bold text-emerald-400 leading-tight mt-0.5">
                <Clock className="w-3 h-3 text-emerald-400 animate-pulse" />
                <span>{istTime}</span>
                <span className="text-[8px] font-mono font-bold px-1 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  IST
                </span>
              </div>
            </div>

          </div>
        </div>
      </div>
    </header>
  );
};
