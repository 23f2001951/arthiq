import React, { useState, useEffect, useMemo } from 'react';
import { TrendingUp, Zap, AlertCircle } from 'lucide-react';
import { fetchMFNavHistory } from '../../api/client';

interface MFNavChartProps {
  schemeCode: number;
  schemeName?: string;
  currentNav?: number;
}

interface NavPoint {
  date: string;
  nav: number;
}

export const MFNavChart: React.FC<MFNavChartProps> = ({
  schemeCode,
  schemeName,
  currentNav,
}) => {
  const [period, setPeriod] = useState<string>('1y');
  const [points, setPoints] = useState<NavPoint[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  useEffect(() => {
    let isCancelled = false;
    setIsLoading(true);
    setError(null);
    setHoverIndex(null);

    fetchMFNavHistory(schemeCode, period)
      .then((res) => {
        if (!isCancelled) {
          if (res && res.points && res.points.length > 0) {
            setPoints(res.points);
          } else {
            setPoints([]);
          }
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          console.error('Failed to load NAV history', err);
          setError('NAV history not available for this period');
        }
      })
      .finally(() => {
        if (!isCancelled) setIsLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [schemeCode, period]);

  // Statistics
  const stats = useMemo(() => {
    if (points.length < 2) return null;
    const navs = points.map((p) => p.nav);
    const minNav = Math.min(...navs);
    const maxNav = Math.max(...navs);
    const startNav = navs[0];
    const endNav = navs[navs.length - 1];
    const absChange = endNav - startNav;
    const pctChange = (absChange / startNav) * 100;
    const minIdx = navs.indexOf(minNav);
    const maxIdx = navs.indexOf(maxNav);
    return {
      minNav,
      maxNav,
      startNav,
      endNav,
      absChange,
      pctChange,
      minIdx,
      maxIdx,
    };
  }, [points]);

  // SVG Chart Dimensions
  const width = 760;
  const height = 240;
  const padding = { top: 20, right: 24, bottom: 28, left: 52 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const minVal = stats ? stats.minNav * 0.985 : 0;
  const maxVal = stats ? stats.maxNav * 1.015 : 100;
  const range = maxVal - minVal || 1;

  const getX = (idx: number) => padding.left + (idx / Math.max(1, points.length - 1)) * chartW;
  const getY = (val: number) => padding.top + chartH - ((val - minVal) / range) * chartH;

  // Catmull-Rom cubic Bezier spline
  const linePath = useMemo(() => {
    if (points.length === 0) return '';
    if (points.length === 1) return `M ${getX(0).toFixed(1)},${getY(points[0].nav).toFixed(1)}`;

    const coords = points.map((p, idx) => ({ x: getX(idx), y: getY(p.nav) }));
    let d = `M ${coords[0].x.toFixed(1)},${coords[0].y.toFixed(1)}`;

    for (let i = 0; i < coords.length - 1; i++) {
      const p0 = i > 0 ? coords[i - 1] : coords[i];
      const p1 = coords[i];
      const p2 = coords[i + 1];
      const p3 = i < coords.length - 2 ? coords[i + 2] : p2;

      const tension = 0.18;
      const cp1x = p1.x + (p2.x - p0.x) * tension;
      const cp1y = p1.y + (p2.y - p0.y) * tension;
      const cp2x = p2.x - (p3.x - p1.x) * tension;
      const cp2y = p2.y - (p3.y - p1.y) * tension;

      d += ` C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return d;
  }, [points, minVal, maxVal]);

  const areaPath = useMemo(() => {
    if (!linePath || points.length === 0) return '';
    const firstX = getX(0).toFixed(1);
    const lastX = getX(points.length - 1).toFixed(1);
    const bottomY = (padding.top + chartH).toFixed(1);
    return `${linePath} L ${lastX},${bottomY} L ${firstX},${bottomY} Z`;
  }, [linePath, points]);

  // Active hover point
  const activePoint = hoverIndex !== null && points[hoverIndex] ? points[hoverIndex] : null;
  const activeChangePct =
    activePoint && stats
      ? ((activePoint.nav - stats.startNav) / stats.startNav) * 100
      : null;

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (points.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const svgX = (mouseX / rect.width) * width;
    const clampedX = Math.max(padding.left, Math.min(padding.left + chartW, svgX));
    const ratio = (clampedX - padding.left) / chartW;
    const idx = Math.round(ratio * (points.length - 1));
    setHoverIndex(Math.max(0, Math.min(points.length - 1, idx)));
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
  };

  const isPositive = stats ? stats.pctChange >= 0 : true;
  const strokeColor = isPositive ? '#10b981' : '#f43f5e';

  const periods = [
    { key: '1m', label: '1M' },
    { key: '3m', label: '3M' },
    { key: '6m', label: '6M' },
    { key: '1y', label: '1Y' },
    { key: '3y', label: '3Y' },
    { key: '5y', label: '5Y' },
    { key: 'max', label: 'MAX' },
  ];

  return (
    <div className="bg-slate-900/70 rounded-2xl border border-slate-800/80 p-5 space-y-4 shadow-lg">
      {/* Top Header & Period Selector */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/70 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <TrendingUp className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              Historical NAV Trajectory
              {isLoading && (
                <span className="text-[10px] text-amber-400 font-normal animate-pulse">
                  (Loading...)
                </span>
              )}
            </h3>
            <p className="text-[11px] text-slate-400 truncate max-w-sm">
              {schemeName || 'Interactive high-resolution net asset value time-series'}
            </p>
          </div>
        </div>

        {/* Period Selector Tabs */}
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
          {periods.map((p) => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg transition-all ${
                period === p.key
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Snapshot Summary Bar */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
            <span className="text-[10px] text-slate-400 uppercase font-medium">Selected NAV</span>
            <p className="text-base font-extrabold text-white mt-0.5">
              ₹{(activePoint ? activePoint.nav : (currentNav ?? stats.endNav)).toFixed(2)}
            </p>
            <span className="text-[10px] text-slate-400">
              {activePoint ? activePoint.date : 'Latest Available'}
            </span>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
            <span className="text-[10px] text-slate-400 uppercase font-medium">{period.toUpperCase()} Return</span>
            <p
              className={`text-base font-extrabold mt-0.5 ${
                (activeChangePct ?? stats.pctChange) >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {(activeChangePct ?? stats.pctChange) >= 0 ? '+' : ''}
              {(activeChangePct ?? stats.pctChange).toFixed(2)}%
            </p>
            <span className="text-[10px] text-slate-400">
              {(activePoint ? activePoint.nav - stats.startNav : stats.absChange) >= 0 ? '+' : ''}
              ₹{(activePoint ? activePoint.nav - stats.startNav : stats.absChange).toFixed(2)} abs
            </span>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
            <span className="text-[10px] text-slate-400 uppercase font-medium">Period High</span>
            <p className="text-sm font-bold text-slate-200 mt-0.5">₹{stats.maxNav.toFixed(2)}</p>
            <span className="text-[10px] text-slate-400">{points[stats.maxIdx]?.date}</span>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
            <span className="text-[10px] text-slate-400 uppercase font-medium">Period Low</span>
            <p className="text-sm font-bold text-slate-200 mt-0.5">₹{stats.minNav.toFixed(2)}</p>
            <span className="text-[10px] text-slate-400">{points[stats.minIdx]?.date}</span>
          </div>
        </div>
      )}

      {/* SVG Canvas */}
      <div className="relative w-full overflow-hidden select-none">
        {isLoading && points.length === 0 ? (
          <div className="h-56 flex flex-col items-center justify-center text-xs text-slate-500">
            <Zap className="h-6 w-6 text-emerald-400/60 animate-pulse mb-1.5" />
            <span>Fetching historical NAV time-series...</span>
          </div>
        ) : error || points.length === 0 ? (
          <div className="h-56 flex flex-col items-center justify-center text-xs text-slate-500">
            <AlertCircle className="h-6 w-6 text-amber-400/60 mb-1.5" />
            <span>{error || 'No historical data available for this range.'}</span>
          </div>
        ) : (
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-auto overflow-visible cursor-crosshair"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          >
            <defs>
              <linearGradient id={`nav-grad-${schemeCode}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={strokeColor} stopOpacity="0.25" />
                <stop offset="85%" stopColor={strokeColor} stopOpacity="0.02" />
                <stop offset="100%" stopColor={strokeColor} stopOpacity="0.00" />
              </linearGradient>
              <filter id="nav-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor={strokeColor} floodOpacity="0.3" />
              </filter>
            </defs>

            {/* Horizontal Gridlines */}
            {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
              const yVal = minVal + pct * range;
              const yPos = getY(yVal);
              return (
                <g key={pct}>
                  <line
                    x1={padding.left}
                    y1={yPos}
                    x2={width - padding.right}
                    y2={yPos}
                    stroke="rgba(255, 255, 255, 0.06)"
                    strokeDasharray="3 3"
                    strokeWidth="1"
                  />
                  <text
                    x={padding.left - 8}
                    y={yPos + 3}
                    fill="rgba(148, 163, 184, 0.7)"
                    fontSize="9"
                    fontFamily="monospace"
                    textAnchor="end"
                  >
                    ₹{yVal.toFixed(1)}
                  </text>
                </g>
              );
            })}

            {/* Date Gridlines & Labels */}
            {points.length > 4 &&
              [0, Math.floor(points.length * 0.33), Math.floor(points.length * 0.66), points.length - 1].map((idx) => {
                const pt = points[idx];
                if (!pt) return null;
                const xPos = getX(idx);
                return (
                  <text
                    key={idx}
                    x={xPos}
                    y={height - 8}
                    fill="rgba(148, 163, 184, 0.6)"
                    fontSize="9"
                    fontFamily="monospace"
                    textAnchor={idx === 0 ? 'start' : idx === points.length - 1 ? 'end' : 'middle'}
                  >
                    {pt.date}
                  </text>
                );
              })}

            {/* Area Fill */}
            <path d={areaPath} fill={`url(#nav-grad-${schemeCode})`} />

            {/* Spline Curve */}
            <path
              d={linePath}
              fill="none"
              stroke={strokeColor}
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter="url(#nav-glow)"
            />

            {/* Min and Max Markers */}
            {stats && (
              <>
                <circle
                  cx={getX(stats.maxIdx)}
                  cy={getY(stats.maxNav)}
                  r="3.5"
                  fill="#10b981"
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
                <circle
                  cx={getX(stats.minIdx)}
                  cy={getY(stats.minNav)}
                  r="3.5"
                  fill="#f43f5e"
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
              </>
            )}

            {/* Hover Crosshair & Pointer */}
            {hoverIndex !== null && activePoint && (
              <g>
                {/* Vertical Line */}
                <line
                  x1={getX(hoverIndex)}
                  y1={padding.top}
                  x2={getX(hoverIndex)}
                  y2={padding.top + chartH}
                  stroke="rgba(255, 255, 255, 0.4)"
                  strokeWidth="1.2"
                  strokeDasharray="3 3"
                />

                {/* Point Halo */}
                <circle
                  cx={getX(hoverIndex)}
                  cy={getY(activePoint.nav)}
                  r="6"
                  fill={strokeColor}
                  opacity="0.3"
                />
                <circle
                  cx={getX(hoverIndex)}
                  cy={getY(activePoint.nav)}
                  r="3.5"
                  fill="#ffffff"
                  stroke={strokeColor}
                  strokeWidth="2"
                />

                {/* Tooltip Overlay */}
                <g
                  transform={`translate(${
                    getX(hoverIndex) > width - 120
                      ? getX(hoverIndex) - 110
                      : getX(hoverIndex) < 110
                      ? getX(hoverIndex) + 10
                      : getX(hoverIndex) - 50
                  }, ${Math.max(padding.top + 4, getY(activePoint.nav) - 46)})`}
                >
                  <rect
                    width="100"
                    height="40"
                    rx="8"
                    fill="#0f172a"
                    stroke="rgba(255, 255, 255, 0.2)"
                    strokeWidth="1"
                    filter="drop-shadow(0 4px 6px rgba(0,0,0,0.5))"
                  />
                  <text x="50" y="15" fill="#94a3b8" fontSize="8" fontFamily="sans-serif" textAnchor="middle">
                    {activePoint.date}
                  </text>
                  <text
                    x="50"
                    y="31"
                    fill="#ffffff"
                    fontSize="11"
                    fontWeight="bold"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    ₹{activePoint.nav.toFixed(2)}
                  </text>
                </g>
              </g>
            )}
          </svg>
        )}
      </div>
    </div>
  );
};
