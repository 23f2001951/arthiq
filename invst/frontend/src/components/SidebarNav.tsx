import React from 'react';
import {
  LayoutDashboard,
  Sparkles,
  Search,
  Briefcase,
  Target,
  Sliders,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  LogOut,
  X,
} from 'lucide-react';
import { NavTab } from './Navbar';

interface SidebarNavProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  systemHealthy: boolean;
  onLogout?: () => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItemConfig {
  id: NavTab;
  label: string;
  category?: string;
  badge?: string;
  badgeColor?: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
  currentTab,
  onSelectTab,
  isCollapsed,
  onToggleCollapse,
  systemHealthy,
  onLogout,
  mobileOpen,
  onCloseMobile,
}) => {
  const navSections: { category: string; items: NavItemConfig[] }[] = [
    {
      category: 'Intelligence',
      items: [
        {
          id: 'dashboard',
          label: 'Dashboard',
          badge: 'LIVE',
          badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
          icon: LayoutDashboard,
        },
        {
          id: 'recommendations',
          label: 'Stock Ideas',
          badge: 'ALPHA',
          badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
          icon: Sparkles,
        },
        {
          id: 'analyzer',
          label: 'Stock Analyzer',
          badge: 'NEW',
          badgeColor: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
          icon: Search,
        },
      ],
    },
    {
      category: 'Portfolio & Risk',
      items: [
        {
          id: 'portfolio',
          label: 'My Portfolio',
          badge: 'HEALTH',
          badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
          icon: Briefcase,
        },
        {
          id: 'targetlist',
          label: 'Target Lists',
          badge: 'WISHLIST',
          badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
          icon: Target,
        },
      ],
    },
    {
      category: 'Quant Lab',
      items: [
        {
          id: 'backtest',
          label: 'Backtest Lab',
          icon: Sliders,
        },
        {
          id: 'health',
          label: 'System Health',
          icon: ShieldCheck,
        },
      ],
    },
  ];

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40 lg:hidden transition-opacity"
        />
      )}

      <aside
        className={`z-50 flex flex-col bg-[#06080e] border-r border-white/[0.07] transition-all duration-300 ease-in-out shrink-0 select-none ${
          isCollapsed ? 'w-20' : 'w-64'
        } h-screen sticky top-0 ${
          mobileOpen
            ? 'fixed inset-y-0 left-0 flex shadow-2xl'
            : 'hidden lg:flex'
        }`}
      >
        {/* 1. Header: Logo & Branding */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-white/[0.06] bg-[#080b13]/80 backdrop-blur-md">
          {!isCollapsed ? (
            <div className="flex items-center justify-between w-full">
              <div
                className="flex items-center space-x-3 cursor-pointer group"
                onClick={() => {
                  onSelectTab('dashboard');
                  if (onCloseMobile) onCloseMobile();
                }}
              >
                <div className="relative shrink-0">
                  <img
                    src="/Arth_IQ.png"
                    alt="Arth IQ"
                    className="w-9 h-9 rounded-xl object-contain bg-black/60 border border-amber-500/30 shadow-[0_0_12px_rgba(234,179,8,0.25)] group-hover:border-amber-400/60 transition-all"
                  />
                  <span
                    className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ring-2 ring-[#080b13] ${
                      systemHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                    }`}
                  />
                </div>
                <div className="overflow-hidden">
                  <div className="flex items-center space-x-1.5">
                    <span className="font-black text-base tracking-tight text-white">
                      ARTH <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-300 to-yellow-200">IQ</span>
                    </span>
                  </div>
                  <p className="text-[8px] font-mono text-slate-400 uppercase tracking-widest truncate">
                    Quant Intelligence
                  </p>
                </div>
              </div>

              {/* Close button visible only on mobile */}
              {mobileOpen && onCloseMobile && (
                <button
                  onClick={onCloseMobile}
                  className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08]"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ) : (
          <div
            className="w-full flex justify-center cursor-pointer group"
            onClick={() => onSelectTab('dashboard')}
          >
            <div className="relative">
              <img
                src="/Arth_IQ.png"
                alt="Arth IQ"
                className="w-9 h-9 rounded-xl object-contain bg-black/60 border border-amber-500/30 shadow-[0_0_12px_rgba(234,179,8,0.25)] group-hover:border-amber-400/60 transition-all"
              />
              <span
                className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full ring-2 ring-[#080b13] ${
                  systemHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`}
              />
            </div>
          </div>
        )}
      </div>

      {/* 2. Navigation Items List */}
      <div className="flex-1 overflow-y-auto py-4 px-2 space-y-6 custom-scrollbar">
        {navSections.map((section, idx) => (
          <div key={idx} className="space-y-1">
            {!isCollapsed && (
              <div className="px-3 pb-1 text-[10px] font-mono font-bold tracking-wider text-slate-500 uppercase">
                {section.category}
              </div>
            )}
            {isCollapsed && idx > 0 && (
              <div className="my-2 border-t border-white/[0.06] mx-2" />
            )}

            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;

              return (
                <div key={item.id} className="relative group">
                  <button
                    onClick={() => onSelectTab(item.id)}
                    className={`w-full flex items-center rounded-xl transition-all duration-200 cursor-pointer ${
                      isCollapsed
                        ? 'justify-center p-3.5'
                        : 'justify-between px-3.5 py-2.5'
                    } ${
                      isActive
                        ? 'bg-gradient-to-r from-winsor-700 to-winsor-600 text-white shadow-[0_0_18px_rgba(37,99,235,0.45)] border border-sky-400/40'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-white/[0.04]'
                    }`}
                  >
                    <div className="flex items-center space-x-3 truncate">
                      <Icon
                        className={`w-5 h-5 shrink-0 transition-transform group-hover:scale-110 ${
                          isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
                        }`}
                      />
                      {!isCollapsed && (
                        <span className="text-xs font-semibold tracking-tight truncate">
                          {item.label}
                        </span>
                      )}
                    </div>

                    {!isCollapsed && item.badge && (
                      <span
                        className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-md border uppercase ${
                          isActive
                            ? 'bg-white/20 text-white border-white/30'
                            : item.badgeColor || 'bg-white/[0.04] text-slate-400 border-white/[0.08]'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}

                    {/* Active Pip Indicator on Left Edge for collapsed mode */}
                    {isCollapsed && isActive && (
                      <span className="absolute left-1 top-2.5 bottom-2.5 w-1 rounded-full bg-sky-400 shadow-[0_0_8px_#38bdf8]" />
                    )}
                  </button>

                  {/* Tooltip on Hover for Collapsed Mode */}
                  {isCollapsed && (
                    <div className="fixed left-20 ml-2 px-3 py-1.5 bg-[#0b0f19] border border-white/10 rounded-lg shadow-2xl opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity z-50 whitespace-nowrap text-left">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-white">{item.label}</span>
                        {item.badge && (
                          <span
                            className={`text-[9px] font-mono font-bold px-1 rounded uppercase ${
                              item.badgeColor || 'bg-white/10 text-slate-300'
                            }`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {section.category}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* 3. Bottom User Profile & Minimize Toggle Controls */}
      <div className="p-3 border-t border-white/[0.06] bg-[#070912]/90 space-y-2">
        {/* User Card */}
        <div
          className={`flex items-center rounded-xl p-2 bg-[#0a0e19] border border-white/[0.06] ${
            isCollapsed ? 'justify-center' : 'justify-between'
          }`}
        >
          <div className="flex items-center space-x-2.5 overflow-hidden">
            <div className="w-7 h-7 shrink-0 rounded-full bg-gradient-to-tr from-amber-500 via-amber-400 to-yellow-200 text-black flex items-center justify-center font-black text-xs shadow-md">
              M
            </div>
            {!isCollapsed && (
              <div className="overflow-hidden">
                <div className="text-xs font-bold text-slate-200 truncate">Mandeep</div>
                <div className="text-[9px] font-mono text-emerald-400 flex items-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1 animate-pulse" />
                  PRO INVESTOR
                </div>
              </div>
            )}
          </div>

          {!isCollapsed && onLogout && (
            <button
              onClick={onLogout}
              title="Sign Out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Collapsible Minimize / Expand Toggle Button */}
        <button
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expand Sidebar' : 'Minimize Sidebar'}
          className="w-full flex items-center justify-center p-2 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] text-slate-400 hover:text-white border border-white/[0.05] transition-all cursor-pointer group"
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 transition-transform group-hover:scale-125 text-amber-400" />
          ) : (
            <div className="flex items-center space-x-2 text-xs font-mono font-medium">
              <ChevronLeft className="w-4 h-4 text-amber-400" />
              <span>Minimize Sidebar</span>
            </div>
          )}
        </button>
      </div>
    </aside>
  </>
);
};
