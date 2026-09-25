import React, { useState, useMemo, useRef } from 'react';
import { Target } from 'lucide-react';

interface PriceRangeLadderProps {
  currentPrice: number;
  low52w: number;
  high52w: number;
  dma50?: number;
  dma200?: number;
  dipTargetPrice?: number;
}

interface TrackPoint {
  id: string;
  label: string;
  price: number;
  pct: number;
  tag: string;
  color: string;
  dotColor: string;
  diffFromCmp: string;
  description: string;
}

export const PriceRangeLadder: React.FC<PriceRangeLadderProps> = ({
  currentPrice,
  low52w,
  high52w,
  dma50,
  dma200,
  dipTargetPrice,
}) => {
  const [hoveredPointId, setHoveredPointId] = useState<string | null>(null);
  const [trackHoverPct, setTrackHoverPct] = useState<number | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);

  const minVal = Math.min(low52w, dipTargetPrice || low52w, currentPrice) * 0.98;
  const maxVal = Math.max(high52w, currentPrice) * 1.02;
  const range = maxVal - minVal || 1;

  const getPercent = (val: number) => {
    return Math.min(97, Math.max(3, ((val - minVal) / range) * 100));
  };

  const pctFromLow = (((currentPrice - low52w) / (low52w || 1)) * 100).toFixed(1);
  const pctFromHigh = (((currentPrice - high52w) / (high52w || 1)) * 100).toFixed(1);

  const getDiffText = (p: number) => {
    if (Math.abs(p - currentPrice) < 0.01) return 'Live CMP';
    const diff = (((p - currentPrice) / currentPrice) * 100);
    return diff > 0 ? `+${diff.toFixed(1)}% vs CMP` : `${diff.toFixed(1)}% vs CMP`;
  };

  // Compile all key points along the ladder
  const trackPoints: TrackPoint[] = useMemo(() => {
    const list: TrackPoint[] = [
      {
        id: '52w_low',
        label: '52W Low',
        price: low52w,
        pct: getPercent(low52w),
        tag: 'Support Floor',
        color: 'text-slate-300',
        dotColor: 'bg-slate-400',
        diffFromCmp: getDiffText(low52w),
        description: 'Lowest traded price in past 52 weeks',
      },
    ];

    if (dipTargetPrice && dipTargetPrice > 0) {
      list.push({
        id: 'dip',
        label: 'Dip Target',
        price: dipTargetPrice,
        pct: getPercent(dipTargetPrice),
        tag: 'Accumulation Zone',
        color: 'text-emerald-400',
        dotColor: 'bg-emerald-400',
        diffFromCmp: getDiffText(dipTargetPrice),
        description: 'Algorithmic value discount entry target',
      });
    }

    list.push({
      id: 'cmp',
      label: 'Live CMP',
      price: currentPrice,
      pct: getPercent(currentPrice),
      tag: 'Current Price',
      color: 'text-sky-300',
      dotColor: 'bg-sky-400',
      diffFromCmp: 'At Market',
      description: 'Latest real-time traded market price',
    });

    if (dma50 && dma50 > 0) {
      list.push({
        id: 'dma50',
        label: '50-DMA',
        price: dma50,
        pct: getPercent(dma50),
        tag: currentPrice >= dma50 ? 'Above 50D Trend' : 'Below 50D Trend',
        color: 'text-cyan-400',
        dotColor: 'bg-cyan-400',
        diffFromCmp: getDiffText(dma50),
        description: '50-day short-term institutional moving average',
      });
    }

    if (dma200 && dma200 > 0) {
      list.push({
        id: 'dma200',
        label: '200-DMA',
        price: dma200,
        pct: getPercent(dma200),
        tag: currentPrice >= dma200 ? 'Bull Structural' : 'Bear Structural',
        color: 'text-purple-400',
        dotColor: 'bg-purple-400',
        diffFromCmp: getDiffText(dma200),
        description: '200-day long-term structural trendline',
      });
    }

    list.push({
      id: '52w_high',
      label: '52W High',
      price: high52w,
      pct: getPercent(high52w),
      tag: 'Resistance Peak',
      color: 'text-slate-300',
      dotColor: 'bg-slate-400',
      diffFromCmp: getDiffText(high52w),
      description: '52-week all-time peak resistance level',
    });

    return list;
  }, [currentPrice, low52w, high52w, dma50, dma200, dipTargetPrice, minVal, range]);

  const activeHoverPoint = useMemo(() => {
    return trackPoints.find((p) => p.id === hoveredPointId) || null;
  }, [trackPoints, hoveredPointId]);

  // Handle free track scrub hover
  const handleTrackMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = Math.min(100, Math.max(0, (x / rect.width) * 100));
    setTrackHoverPct(pct);

    // Auto-detect closest point if within 4%
    const nearest = trackPoints.find((p) => Math.abs(p.pct - pct) < 4.0);
    setHoveredPointId(nearest ? nearest.id : null);
  };

  const handleTrackMouseLeave = () => {
    setTrackHoverPct(null);
    setHoveredPointId(null);
  };

  const lowPct = getPercent(low52w);
  const highPct = getPercent(high52w);
  const dipPct = dipTargetPrice && dipTargetPrice > 0 ? getPercent(dipTargetPrice) : null;
  const cmpPct = getPercent(currentPrice);

  return (
    <div className="glass-panel p-5 rounded-3xl relative overflow-hidden space-y-4 select-none">
      {/* Background ambient corner glow */}
      <div className="absolute top-0 right-1/4 w-80 h-32 bg-sky-500/5 blur-3xl pointer-events-none" />

      {/* Header with Title and 52W extremes */}
      <div className="flex flex-wrap items-center justify-between gap-3 relative z-10">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.2)]">
            <Target className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-black uppercase tracking-wider text-white flex items-center gap-1.5">
              52-Week Range &amp; Institutional Key Levels
              <span className="text-[9px] px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-300 border border-sky-500/30 font-mono font-bold">
                HOVERABLE LADDER
              </span>
            </h4>
            <p className="text-[10px] text-slate-400">
              Hover any point or scrub across the track to inspect live price distance and entry buffers
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5 text-xs font-mono font-bold">
          <span className="text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded-xl border border-emerald-500/30 shadow-sm">
            +{pctFromLow}% from 52W Low
          </span>
          <span className="text-rose-400 bg-rose-950/40 px-2.5 py-1 rounded-xl border border-rose-500/30 shadow-sm">
            {pctFromHigh}% from 52W High
          </span>
        </div>
      </div>

      {/* Interactive Track Area with Hover Tooltips */}
      <div className="relative pt-12 pb-6 px-4">
        {/* Active Point Hover Tooltip floating right above the point */}
        {activeHoverPoint && (
          <div
            className="absolute top-0 -translate-x-1/2 z-30 px-3.5 py-1.5 rounded-xl bg-[#070b16] border border-sky-400/60 shadow-[0_0_20px_rgba(56,189,248,0.35)] text-center pointer-events-none whitespace-nowrap transition-all duration-200 animate-fadeIn"
            style={{ left: `${activeHoverPoint.pct}%` }}
          >
            <div className="flex items-center justify-center space-x-1.5 font-mono text-[10px] font-bold text-sky-300 uppercase tracking-wider">
              <span>{activeHoverPoint.label}</span>
              <span className="text-white/40">•</span>
              <span className="text-slate-300">{activeHoverPoint.tag}</span>
            </div>
            <div className="text-xs font-mono font-black text-white mt-0.5">
              ₹{activeHoverPoint.price.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
              <span className="text-[10px] font-semibold text-slate-400 ml-1.5 font-mono">
                ({activeHoverPoint.diffFromCmp})
              </span>
            </div>
            {/* Tooltip downward pointer notch */}
            <div className="absolute left-1/2 -bottom-1 -translate-x-1/2 w-2 h-2 rotate-45 bg-[#070b16] border-r border-b border-sky-400/60" />
          </div>
        )}

        {/* The Track Container (Captures mouse moves across the entire width) */}
        <div
          ref={trackRef}
          onMouseMove={handleTrackMouseMove}
          onMouseLeave={handleTrackMouseLeave}
          className="relative w-full h-4 bg-[#030509] rounded-full border border-white/[0.1] shadow-inner cursor-crosshair overflow-visible group"
        >
          {/* 52W Range Gradient Span */}
          <div
            className="absolute top-0 bottom-0 bg-gradient-to-r from-sky-900/60 via-winsor-700/50 to-indigo-900/60 rounded-full"
            style={{
              left: `${lowPct}%`,
              width: `${Math.max(3, highPct - lowPct)}%`,
            }}
          />

          {/* Dip Target Accumulation Zone */}
          {dipPct !== null && (
            <div
              className="absolute top-0 bottom-0 bg-emerald-500/30 border-r border-emerald-400"
              style={{
                left: `${Math.min(dipPct, cmpPct)}%`,
                width: `${Math.abs(cmpPct - dipPct)}%`,
              }}
              title="Accumulation Margin"
            />
          )}

          {/* Scrubbing Cursor Crosshair Line */}
          {trackHoverPct !== null && (
            <div
              className="absolute top--2 bottom--2 w-[1px] bg-sky-400/80 pointer-events-none transition-all"
              style={{ left: `${trackHoverPct}%` }}
            />
          )}

          {/* Interactive Points on the Line */}
          {trackPoints.map((pt) => {
            const isHovered = hoveredPointId === pt.id;
            const isCmp = pt.id === 'cmp';
            const isDip = pt.id === 'dip';

            return (
              <div
                key={pt.id}
                onMouseEnter={() => setHoveredPointId(pt.id)}
                onMouseLeave={() => setHoveredPointId(null)}
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 cursor-pointer z-20 group"
                style={{ left: `${pt.pct}%` }}
              >
                {/* Large invisible touch/hover hit zone (32x32px) */}
                <div className="w-8 h-8 -ml-1 -mt-1 flex items-center justify-center">
                  {/* Glowing aura when hovered */}
                  {isHovered && (
                    <div
                      className={`absolute ${
                        isCmp
                          ? 'w-2.5 h-8 bg-sky-400/40 rounded-full blur-[2px]'
                          : isDip
                          ? 'w-6 h-6 rounded-full bg-emerald-400/30 animate-ping'
                          : 'w-6 h-6 rounded-full bg-white/20 animate-ping'
                      } pointer-events-none`}
                    />
                  )}

                  {/* Main Point Marker on the Track */}
                  {isCmp ? (
                    <div className="relative flex items-center justify-center">
                      {/* Live Price single vertical line cutting through the track */}
                      <div
                        className={`w-[2.5px] h-7 rounded-full bg-sky-400 shadow-[0_0_12px_rgba(56,189,248,0.95)] transition-all duration-150 ${
                          isHovered ? 'w-[3.5px] h-8 bg-sky-300 shadow-[0_0_18px_rgba(56,189,248,1)]' : ''
                        }`}
                      />
                    </div>
                  ) : isDip ? (
                    <div className="w-3.5 h-3.5 rotate-45 bg-emerald-400 shadow-[0_0_10px_#34d399] border-2 border-slate-950" />
                  ) : (
                    <div
                      className={`w-3 h-3 rounded-full ${pt.dotColor} border-2 border-slate-950 transition-all ${
                        isHovered ? 'scale-125 shadow-[0_0_10px_currentColor]' : ''
                      }`}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Minimal Price Labels Directly Below the Line */}
        <div className="relative w-full h-5 mt-2">
          {trackPoints.map((pt) => {
            const isHovered = hoveredPointId === pt.id;
            return (
              <div
                key={`label-${pt.id}`}
                onMouseEnter={() => setHoveredPointId(pt.id)}
                onMouseLeave={() => setHoveredPointId(null)}
                className="absolute top-0 -translate-x-1/2 flex flex-col items-center cursor-pointer pointer-events-auto"
                style={{ left: `${pt.pct}%` }}
              >
                <span
                  className={`text-[9px] font-mono font-bold transition-all whitespace-nowrap ${
                    isHovered ? 'text-sky-300 scale-110' : 'text-slate-500'
                  }`}
                >
                  {pt.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Key Levels Interactive Matrix Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-3 border-t border-white/[0.06]">
        {trackPoints.map((pt) => {
          const isHovered = hoveredPointId === pt.id;
          const isCmp = pt.id === 'cmp';

          return (
            <div
              key={`card-${pt.id}`}
              onMouseEnter={() => setHoveredPointId(pt.id)}
              onMouseLeave={() => setHoveredPointId(null)}
              className={`p-2.5 rounded-2xl bg-[#060912] border transition-all duration-200 cursor-pointer ${
                isHovered
                  ? 'border-sky-400/80 bg-[#091024] shadow-[0_0_15px_rgba(56,189,248,0.25)] scale-[1.02]'
                  : isCmp
                  ? 'border-sky-500/40 bg-[#080d1e]'
                  : 'border-white/[0.06] hover:border-white/[0.14]'
              }`}
            >
              <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                <span className="font-bold">{pt.label}</span>
                {isCmp ? (
                  <span className="w-1 h-3 rounded-full bg-sky-400 shadow-[0_0_8px_#38bdf8]" />
                ) : (
                  <span className={`w-2 h-2 rounded-full ${pt.dotColor}`} />
                )}
              </div>
              <div className="mt-1 flex items-baseline justify-between">
                <span className={`text-xs font-mono font-black ${pt.color}`}>
                  ₹{pt.price.toLocaleString('en-IN', { maximumFractionDigits: 1 })}
                </span>
              </div>
              <div className="text-[9px] font-mono text-slate-500 truncate mt-0.5">
                {pt.diffFromCmp}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PriceRangeLadder;
