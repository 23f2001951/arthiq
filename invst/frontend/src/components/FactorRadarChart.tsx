import React, { useState, useRef } from 'react';
import { Sparkles, Info } from 'lucide-react';

export interface FactorRadarData {
  axis: string;
  score: number; // 0 - 100
  benchmark?: number; // 0 - 100
  description?: string;
}

interface FactorRadarChartProps {
  data: FactorRadarData[];
  size?: number;
  stockName?: string;
}

export const FactorRadarChart: React.FC<FactorRadarChartProps> = ({
  data,
  size = 280,
}) => {
  const [hoveredAxis, setHoveredAxis] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const cx = size / 2;
  const cy = size / 2;
  const radius = (size / 2) - 44;
  const count = data.length || 6;

  // Grid levels (25%, 50%, 75%, 100%)
  const levels = [0.25, 0.5, 0.75, 1.0];

  // Helper to convert polar to cartesian
  const getCoordinates = (index: number, valueRatio: number) => {
    // Top axis starts at -PI / 2
    const angle = (Math.PI * 2 / count) * index - Math.PI / 2;
    const x = cx + radius * valueRatio * Math.cos(angle);
    const y = cy + radius * valueRatio * Math.sin(angle);
    return { x, y, angle };
  };

  // Stock Polygon Points
  const stockPoints = data.map((d, i) => {
    const ratio = Math.max(0.1, Math.min(1.0, d.score / 100));
    const { x, y } = getCoordinates(i, ratio);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  // Benchmark Polygon Points (e.g. median 50/100)
  const benchPoints = data.map((d, i) => {
    const ratio = (d.benchmark || 50) / 100;
    const { x, y } = getCoordinates(i, ratio);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  // Global mouse move on SVG to detect closest sector automatically
  const handleSvgMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const scale = size / rect.width;
    const mouseX = (e.clientX - rect.left) * scale - cx;
    const mouseY = (e.clientY - rect.top) * scale - cy;

    const dist = Math.sqrt(mouseX * mouseX + mouseY * mouseY);
    if (dist < 15 || dist > radius * 1.5) {
      return;
    }

    // Angle relative to -PI/2 (top)
    let angle = Math.atan2(mouseY, mouseX) + Math.PI / 2;
    if (angle < 0) angle += Math.PI * 2;
    const slice = (Math.PI * 2) / count;
    const idx = Math.round(angle / slice) % count;
    if (idx >= 0 && idx < count) {
      setHoveredAxis(idx);
    }
  };

  return (
    <div className="relative flex flex-col items-center justify-center p-2 select-none w-full">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${size} ${size}`}
        className="overflow-visible w-full max-w-[270px] h-auto cursor-crosshair"
        onMouseMove={handleSvgMouseMove}
        onMouseLeave={() => setHoveredAxis(null)}
      >
        <defs>
          {/* Radar area glowing gradient */}
          <radialGradient id="radarAreaGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.45" />
            <stop offset="60%" stopColor="#2563eb" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#1e3a8a" stopOpacity="0.05" />
          </radialGradient>

          {/* Node glow filter */}
          <filter id="radarNodeGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#38bdf8" floodOpacity="0.9" />
          </filter>

          <filter id="radarHoverNodeGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor="#38bdf8" floodOpacity="1" />
          </filter>
        </defs>

        {/* Concentric Web Grid Rings */}
        {levels.map((level, lIdx) => {
          const ringPoints = Array.from({ length: count }).map((_, i) => {
            const { x, y } = getCoordinates(i, level);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
          }).join(' ');

          return (
            <polygon
              key={lIdx}
              points={ringPoints}
              fill="none"
              stroke={lIdx === levels.length - 1 ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.06)'}
              strokeWidth={lIdx === levels.length - 1 ? '1.5' : '1'}
              strokeDasharray={lIdx === levels.length - 1 ? 'none' : '2 3'}
            />
          );
        })}

        {/* Axis Spoke Lines */}
        {data.map((_, i) => {
          const { x, y } = getCoordinates(i, 1.0);
          const isHovered = hoveredAxis === i;
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={x}
              y2={y}
              stroke={isHovered ? '#38bdf8' : 'rgba(255, 255, 255, 0.1)'}
              strokeWidth={isHovered ? '2' : '1'}
              className="transition-all duration-200"
            />
          );
        })}

        {/* Benchmark Area (Dashed Slate) */}
        <polygon
          points={benchPoints}
          fill="none"
          stroke="#64748b"
          strokeWidth="1.5"
          strokeDasharray="3 3"
          opacity="0.6"
          pointerEvents="none"
        />

        {/* Stock Polygon Area */}
        <polygon
          points={stockPoints}
          fill="url(#radarAreaGrad)"
          stroke="#38bdf8"
          strokeWidth="2.5"
          strokeLinejoin="round"
          className="transition-all duration-300"
          pointerEvents="none"
        />

        {/* Large Invisible Hit Targets along Each Spoke for Easy Hover */}
        {data.map((_, i) => {
          const { x, y } = getCoordinates(i, 1.1);
          return (
            <line
              key={`hit-${i}`}
              x1={cx}
              y1={cy}
              x2={x}
              y2={y}
              stroke="transparent"
              strokeWidth="36"
              className="cursor-pointer"
              onMouseEnter={() => setHoveredAxis(i)}
            />
          );
        })}

        {/* Interactive Vertex Nodes */}
        {data.map((d, i) => {
          const ratio = Math.max(0.1, Math.min(1.0, d.score / 100));
          const { x, y } = getCoordinates(i, ratio);
          const isHovered = hoveredAxis === i;

          return (
            <g
              key={i}
              className="cursor-pointer"
              onMouseEnter={() => setHoveredAxis(i)}
            >
              {/* Invisible large hover halo */}
              <circle cx={x} cy={y} r="18" fill="transparent" />

              {/* Pulsing ring on hover */}
              {isHovered && (
                <circle
                  cx={x}
                  cy={y}
                  r="10"
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="1.5"
                  opacity="0.8"
                  className="animate-ping"
                />
              )}

              {/* Visible node */}
              <circle
                cx={x}
                cy={y}
                r={isHovered ? '7' : '4.5'}
                fill={isHovered ? '#ffffff' : '#38bdf8'}
                stroke="#080d1a"
                strokeWidth={isHovered ? '2.5' : '1.5'}
                filter={isHovered ? 'url(#radarHoverNodeGlow)' : 'url(#radarNodeGlow)'}
                className="transition-all duration-200"
              />
            </g>
          );
        })}

        {/* Outer Axis Labels */}
        {data.map((d, i) => {
          const { x, y } = getCoordinates(i, 1.25);
          const isHovered = hoveredAxis === i;

          return (
            <g
              key={i}
              className="cursor-pointer"
              onMouseEnter={() => setHoveredAxis(i)}
            >
              {/* Invisible text hover hit area */}
              <rect
                x={x - 30}
                y={y - 14}
                width="60"
                height="32"
                fill="transparent"
              />

              <text
                x={x}
                y={y - 2}
                textAnchor="middle"
                fontSize="10"
                fontFamily="sans-serif"
                fontWeight={isHovered ? 'bold' : '600'}
                fill={isHovered ? '#38bdf8' : '#94a3b8'}
                className="transition-colors duration-200"
              >
                {d.axis}
              </text>
              <text
                x={x}
                y={y + 11}
                textAnchor="middle"
                fontSize="10"
                fontFamily="monospace"
                fontWeight="bold"
                fill={isHovered ? '#ffffff' : d.score >= 70 ? '#10b981' : d.score >= 50 ? '#38bdf8' : '#f59e0b'}
              >
                {d.score.toFixed(0)}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Floating Active Factor Tooltip with smooth transition */}
      <div className="w-full min-h-[58px] mt-2 flex items-center justify-center">
        {hoveredAxis !== null && data[hoveredAxis] ? (
          <div className="w-full px-3 py-2 rounded-xl bg-[#090e1c] border border-sky-400/40 shadow-xl text-center text-xs animate-fadeIn">
            <div className="flex items-center justify-center gap-1.5 font-bold font-mono text-sky-300">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>{data[hoveredAxis].axis}: {data[hoveredAxis].score.toFixed(1)}/100</span>
              <span className="text-[10px] text-slate-400 font-normal">
                ({data[hoveredAxis].score >= (data[hoveredAxis].benchmark || 50) ? '+' : ''}
                {(data[hoveredAxis].score - (data[hoveredAxis].benchmark || 50)).toFixed(0)} vs Median)
              </span>
            </div>
            {data[hoveredAxis].description && (
              <p className="text-[10px] text-slate-300 mt-0.5 truncate font-sans">
                {data[hoveredAxis].description}
              </p>
            )}
          </div>
        ) : (
          <div className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
            <Info className="w-3.5 h-3.5" />
            <span>Hover any vertex or label to inspect factor diagnosis</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default FactorRadarChart;
