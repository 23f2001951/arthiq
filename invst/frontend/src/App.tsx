import React, { useState, useEffect } from 'react';
import { NavTab } from './components/Navbar';
import { SidebarNav } from './components/SidebarNav';
import { TopHeader } from './components/TopHeader';
import { MarketTickerTape } from './components/MarketTickerTape';
import { StockIdeasSubNav, StockIdeasSubTab } from './components/StockIdeasSubNav';
import { ModernArtboxFooter } from './components/ModernArtboxFooter';
import { AuthGate } from './components/AuthGate';
import { fetchHealth, verifyAuth, logout } from './api/client';

// Lazy-loaded views for optimal SPA performance and code splitting
const DashboardView = React.lazy(() =>
  import('./views/DashboardView').then((m) => ({ default: m.DashboardView }))
);
const RecommendationsView = React.lazy(() =>
  import('./views/RecommendationsView').then((m) => ({ default: m.RecommendationsView }))
);
const StockAnalyzerView = React.lazy(() =>
  import('./views/StockAnalyzerView').then((m) => ({ default: m.StockAnalyzerView }))
);
const PortfolioHealthView = React.lazy(() =>
  import('./views/PortfolioHealthView').then((m) => ({ default: m.PortfolioHealthView }))
);
const TargetListView = React.lazy(() =>
  import('./views/TargetListView').then((m) => ({ default: m.TargetListView }))
);
const BacktestView = React.lazy(() =>
  import('./views/BacktestView').then((m) => ({ default: m.BacktestView }))
);
const HealthView = React.lazy(() =>
  import('./views/HealthView').then((m) => ({ default: m.HealthView }))
);

const ViewLoadingSkeleton: React.FC = () => (
  <div className="space-y-6 animate-pulse py-4">
    <div className="h-28 bg-slate-900/60 rounded-2xl border border-slate-800/80"></div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="h-40 bg-slate-900/60 rounded-2xl border border-slate-800/80"></div>
      <div className="h-40 bg-slate-900/60 rounded-2xl border border-slate-800/80"></div>
      <div className="h-40 bg-slate-900/60 rounded-2xl border border-slate-800/80"></div>
    </div>
    <div className="h-80 bg-slate-900/60 rounded-2xl border border-slate-800/80"></div>
  </div>
);

export const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [currentTab, setCurrentTab] = useState<NavTab>('dashboard');
  const [stockIdeasSubTab, setStockIdeasSubTab] = useState<StockIdeasSubTab>('alpha_picks');
  const [analyzerSymbol, setAnalyzerSymbol] = useState<string>('TCS');
  const [systemHealthy, setSystemHealthy] = useState<boolean>(true);

  // Sidebar collapse state with localStorage persistence
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('arth_sidebar_collapsed');
      return saved !== null ? JSON.parse(saved) : false;
    } catch {
      return false;
    }
  });

  const [isMobileOpen, setIsMobileOpen] = useState<boolean>(false);

  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('arth_sidebar_collapsed', JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  // Check auth session on startup
  useEffect(() => {
    verifyAuth().then((authed) => {
      setIsAuthenticated(authed);
    });

    const handleUnauthorized = () => {
      setIsAuthenticated(false);
    };
    window.addEventListener('arth:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('arth:unauthorized', handleUnauthorized);
    };
  }, []);

  // Fetch health when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      fetchHealth()
        .then((res) => {
          setSystemHealthy(res.overall_status === 'HEALTHY');
        })
        .catch(() => {
          setSystemHealthy(false);
        });
    }
  }, [isAuthenticated]);

  const handleLogout = async () => {
    await logout();
    setIsAuthenticated(false);
  };

  // 1. Initial Checking State
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#040508] text-slate-100 font-sans">
        <div className="relative">
          <img
            src="/Arth_IQ.png"
            alt="Arth IQ"
            className="w-16 h-16 rounded-2xl object-contain bg-black/80 border border-amber-500/30 shadow-2xl p-1 animate-pulse"
          />
        </div>
        <div className="mt-4 text-xs font-mono text-slate-400 tracking-wider">
          INITIALIZING ARTH IQ ENGINE...
        </div>
      </div>
    );
  }

  // 2. Unauthenticated: Render Luxury Auth Gate
  if (!isAuthenticated) {
    return <AuthGate onAuthenticated={() => setIsAuthenticated(true)} />;
  }

  // 3. Authenticated: Render Main Portal with SidebarNav on the Left
  return (
    <div className="min-h-screen flex bg-[#040508] text-slate-100 font-sans selection:bg-winsor-600 selection:text-white">
      {/* Collapsible Left-Side Navigation Bar */}
      <SidebarNav
        currentTab={currentTab}
        onSelectTab={(tab) => {
          setCurrentTab(tab);
          setIsMobileOpen(false);
        }}
        isCollapsed={isCollapsed}
        onToggleCollapse={handleToggleCollapse}
        systemHealthy={systemHealthy}
        onLogout={handleLogout}
        mobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
      />

      {/* Main Content Area (Right) */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Streamlined Top Header */}
        <TopHeader
          currentTab={currentTab}
          systemHealthy={systemHealthy}
          onQuickAction={() => {
            setCurrentTab('analyzer');
          }}
          onOpenMobileSidebar={() => setIsMobileOpen(true)}
        />

        {/* Live Animated Market Ticker Tape */}
        <MarketTickerTape />

        {/* Sub-navbar directly under Market Ticker for Stock Ideas Tab */}
        {currentTab === 'recommendations' && (
          <StockIdeasSubNav
            activeSubTab={stockIdeasSubTab}
            onSelectSubTab={setStockIdeasSubTab}
          />
        )}

        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
          <div key={currentTab} className="animate-fade-in-up space-y-8">
            <React.Suspense fallback={<ViewLoadingSkeleton />}>
              {currentTab === 'dashboard' && (
                <DashboardView
                  onNavigateTab={(tab, subTab) => {
                    setCurrentTab(tab as NavTab);
                    if (subTab) setStockIdeasSubTab(subTab as StockIdeasSubTab);
                  }}
                />
              )}
              {currentTab === 'recommendations' && (
                <RecommendationsView
                  activeSubTab={stockIdeasSubTab}
                  onSelectSubTab={setStockIdeasSubTab}
                />
              )}
              {currentTab === 'analyzer' && (
                <StockAnalyzerView
                  initialSymbol={analyzerSymbol}
                  onNavigateTab={(tab) => setCurrentTab(tab as NavTab)}
                />
              )}
              {currentTab === 'portfolio' && <PortfolioHealthView />}
              {currentTab === 'targetlist' && (
                <TargetListView
                  onNavigateTab={(tab, sym) => {
                    if (sym) setAnalyzerSymbol(sym);
                    setCurrentTab(tab as NavTab);
                  }}
                />
              )}
              {currentTab === 'backtest' && <BacktestView />}
              {currentTab === 'health' && <HealthView />}
            </React.Suspense>
          </div>

          {/* Modern Artbox-Style Footer Card */}
          <ModernArtboxFooter />
        </main>
      </div>
    </div>
  );
};

export default App;
