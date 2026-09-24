import React, { useState, useRef, useEffect } from 'react';
import {
  LayoutDashboard,
  Sparkles,
  LineChart,
  ShieldCheck,
  Plus,
  ChevronDown,
  ExternalLink,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Clock,
  Calendar,
  Lock,
  Search,
  Briefcase,
  Target,
} from 'lucide-react';

export type NavTab = 'dashboard' | 'recommendations' | 'analyzer' | 'portfolio' | 'targetlist' | 'backtest' | 'health';

interface NavbarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  systemHealthy: boolean;
  onQuickAction?: () => void;
  onLogout?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onSelectTab,
  systemHealthy,
  onQuickAction,
  onLogout,
}) => {
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  // Live IST Date & Clock State
  const [istDate, setIstDate] = useState('');
  const [istTime, setIstTime] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      // Date in IST: e.g. "Sun, 20 Sep 2026"
      const dateFormatted = new Intl.DateTimeFormat('en-IN', {
        timeZone: 'Asia/Kolkata',
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }).format(now);

      // Time in IST: e.g. "10:31:05 PM"
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

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const mainTabs = [
    { id: 'dashboard' as NavTab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'recommendations' as NavTab, label: 'Stock Ideas', icon: Sparkles },
    { id: 'analyzer' as NavTab, label: 'Stock Analyzer', icon: Search },
    { id: 'portfolio' as NavTab, label: 'My Portfolio', icon: Briefcase },
    { id: 'targetlist' as NavTab, label: 'Target Lists', icon: Target },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#06070a]/95 backdrop-blur-xl border-b border-white/[0.06]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* 1. Logo & Brand: Arth_IQ.png */}
          <div
            className="flex items-center space-x-3 cursor-pointer group select-none"
            onClick={() => onSelectTab('dashboard')}
          >
            <div className="relative">
              <img
                src="/Arth_IQ.png"
                alt="Arth IQ"
                className="w-10 h-10 rounded-xl object-contain bg-black/60 border border-amber-500/30 shadow-[0_0_15px_rgba(234,179,8,0.25)] group-hover:border-amber-400/60 transition-all"
              />
              <span
                className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ring-2 ring-[#06070a] ${
                  systemHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`}
              />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-black text-lg tracking-tight text-white">
                  ARTH <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-300 to-yellow-200">IQ</span>
                </span>
                <span className="hidden sm:inline text-[9px] font-mono font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  PERSONAL INTELLIGENCE
                </span>
              </div>
              <p className="text-[9px] text-slate-400 tracking-wider hidden md:block uppercase font-medium">
                Research • Analyse • Invest • Grow
              </p>
            </div>
          </div>

          {/* 2. Primary Navigation Tabs (Streamlined: Dashboard + Ideas) */}
          <nav className="flex items-center space-x-1 bg-[#090c14] p-1.5 rounded-full border border-white/[0.06]">
            {mainTabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onSelectTab(tab.id)}
                  className={`flex items-center px-4 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-winsor-700 to-winsor-600 text-white shadow-[0_0_15px_rgba(37,99,235,0.5)] border border-sky-400/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 mr-1.5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* 3. Right Action + Profile Dropdown Container */}
          <div className="flex items-center space-x-3">
            {/* Live IST Date & Clock: Clock below Date */}
            <div className="hidden lg:flex flex-col items-end justify-center px-3 py-1 rounded-2xl bg-[#080b13] border border-white/[0.08] shadow-inner font-mono select-none">
              {/* Top: Date */}
              <div className="flex items-center space-x-1.5 text-[11px] font-semibold text-slate-300 leading-tight">
                <Calendar className="w-3 h-3 text-sky-400" />
                <span>{istDate}</span>
              </div>
              {/* Bottom: Clock below Date */}
              <div className="flex items-center space-x-1.5 text-[11px] font-bold text-emerald-400 leading-tight mt-0.5">
                <Clock className="w-3 h-3 text-emerald-400 animate-pulse" />
                <span>{istTime}</span>
                <span className="text-[9px] font-mono font-bold px-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  IST
                </span>
              </div>
            </div>

            {/* Quick Tactical Order CTA */}
            <button
              onClick={() => {
                if (onQuickAction) {
                  onQuickAction();
                } else {
                  onSelectTab('recommendations');
                }
              }}
              className="hidden sm:flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-gradient-to-r from-winsor-600 to-sky-500 hover:brightness-110 text-white text-xs font-bold shadow-[0_0_15px_rgba(37,99,235,0.4)] transition-all cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 stroke-[3]" />
              <span>Tactical Order</span>
            </button>

            {/* Profile Dropdown (Houses Backtest Lab, PIT Health, API & Settings) */}
            <div className="relative" ref={profileRef}>
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className={`flex items-center space-x-2 px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
                  profileOpen || currentTab === 'backtest' || currentTab === 'health'
                    ? 'bg-[#121625] border-winsor-500/50 shadow-[0_0_15px_rgba(37,99,235,0.25)]'
                    : 'bg-[#0a0d17] border-white/[0.08] hover:border-white/20'
                }`}
              >
                {/* Avatar with gold/winsor gradient */}
                <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-amber-500 via-amber-400 to-yellow-200 text-black flex items-center justify-center font-bold text-xs shadow-md">
                  M
                </div>

                <div className="hidden md:flex flex-col text-left">
                  <span className="text-xs font-bold text-slate-200 leading-tight">Mandeep</span>
                  <span className="text-[9px] font-mono text-amber-400 font-semibold leading-tight">
                    QUANT PRO
                  </span>
                </div>

                <ChevronDown
                  className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${
                    profileOpen ? 'rotate-180 text-winsor-400' : ''
                  }`}
                />
              </button>

              {/* Profile Menu Dropdown */}
              {profileOpen && (
                <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-[#090b14] border border-white/[0.1] shadow-2xl shadow-black/90 p-2 z-50 backdrop-blur-2xl animate-fadeIn">
                  {/* User Card */}
                  <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] mb-2">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-amber-500 to-yellow-300 text-black flex items-center justify-center font-black text-sm">
                        M
                      </div>
                      <div>
                        <p className="text-xs font-bold text-white">Mandeep S.</p>
                        <p className="text-[10px] text-slate-400 font-mono">mandeepsmac@gmail.com</p>
                        <div className="flex items-center space-x-1 mt-1 text-[9px] font-mono text-emerald-400">
                          <CheckCircle2 className="w-2.5 h-2.5" />
                          <span>NSE 500 Verified Access</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Section Label: Advanced Quant Tools */}
                  <div className="px-2 py-1 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider">
                    Advanced Quant Lab
                  </div>

                  {/* 1. Walk-Forward Backtest Lab (Moved under Profile) */}
                  <button
                    onClick={() => {
                      onSelectTab('backtest');
                      setProfileOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                      currentTab === 'backtest'
                        ? 'bg-winsor-950/80 text-winsor-300 border border-winsor-500/40 shadow-sm'
                        : 'text-slate-300 hover:text-white hover:bg-white/[0.04]'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5">
                      <LineChart className="w-4 h-4 text-sky-400" />
                      <div className="text-left">
                        <span className="block font-semibold">Walk-Forward Backtest</span>
                        <span className="text-[10px] text-slate-500 block">Out-of-sample simulation</span>
                      </div>
                    </div>
                    {currentTab === 'backtest' && (
                      <span className="w-1.5 h-1.5 rounded-full bg-winsor-400 shadow-[0_0_8px_#38bdf8]" />
                    )}
                  </button>

                  {/* 2. System & PIT Health Audits (Moved under Profile) */}
                  <button
                    onClick={() => {
                      onSelectTab('health');
                      setProfileOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all mt-1 ${
                      currentTab === 'health'
                        ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 shadow-sm'
                        : 'text-slate-300 hover:text-white hover:bg-white/[0.04]'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <div className="text-left">
                        <span className="block font-semibold">Point-in-Time Health</span>
                        <span className="text-[10px] text-slate-500 block">Zero-lookahead audits</span>
                      </div>
                    </div>
                    <span
                      className={`w-2 h-2 rounded-full ${
                        systemHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                      }`}
                    />
                  </button>

                  {/* Divider */}
                  <div className="my-2 border-t border-white/[0.06]" />

                  {/* Section Label: Strategy & Engine */}
                  <div className="px-2 py-1 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider">
                    Engine & Config
                  </div>

                  {/* Strategy Preferences */}
                  <div className="px-3 py-1.5 text-xs text-slate-400 flex items-center justify-between">
                    <span className="flex items-center space-x-1.5">
                      <Sliders className="w-3.5 h-3.5 text-amber-400" />
                      <span>Model Weights</span>
                    </span>
                    <span className="text-[10px] font-mono text-slate-300">Q30 V25 R25 S20</span>
                  </div>

                  {/* Interactive Swagger Docs Link */}
                  <a
                    href="/docs"
                    target="_blank"
                    rel="noreferrer"
                    className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/[0.04] transition-all"
                  >
                    <div className="flex items-center space-x-2">
                      <ExternalLink className="w-3.5 h-3.5 text-winsor-400" />
                      <span>FastAPI Swagger Docs</span>
                    </div>
                    <span className="text-[9px] font-mono text-slate-500">API v0.1</span>
                  </a>

                  {/* Engine Status indicator */}
                  <div className="mt-2 p-2 rounded-xl bg-[#04060b] border border-white/[0.04] flex items-center justify-between text-[10px] font-mono text-slate-400">
                    <span className="flex items-center">
                      {systemHealthy ? (
                        <CheckCircle2 className="w-3 h-3 text-emerald-400 mr-1" />
                      ) : (
                        <AlertCircle className="w-3 h-3 text-amber-400 mr-1" />
                      )}
                      Engine State
                    </span>
                    <span className={systemHealthy ? 'text-emerald-400 font-bold' : 'text-amber-400'}>
                      {systemHealthy ? 'ACTIVE & AUDITED' : 'ATTENTION'}
                    </span>
                  </div>

                  {/* Lock Engine / Sign Out Action */}
                  {onLogout && (
                    <div className="pt-2 mt-2 border-t border-white/[0.06]">
                      <button
                        onClick={() => {
                          setProfileOpen(false);
                          onLogout();
                        }}
                        className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20 hover:border-rose-500/40 transition-all cursor-pointer group"
                      >
                        <div className="flex items-center space-x-2">
                          <Lock className="w-3.5 h-3.5 text-rose-400 group-hover:scale-110 transition-transform" />
                          <span>Lock Engine (Sign Out)</span>
                        </div>
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300">
                          SECURE
                        </span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
