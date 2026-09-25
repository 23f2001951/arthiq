import React from 'react';

interface TrendSparklineProps {
  data?: number[];
  color?: 'emerald' | 'cyan' | 'rose' | 'amber' | 'violet';
  width?: number;
  height?: number;
  isPositive?: boolean;
}

export const TrendSparkline: React.FC<TrendSparklineProps> = ({
  data,
  color = 'emerald',
  width = 96,
  height = 30,
  isPositive = true,
}) => {
  // Generate a smooth sample trend if no raw array is provided
  const points =
    data && data.length > 2
      ? data
      : isPositive
      ? [10, 12, 11, 14, 13, 16, 15, 18, 17, 21, 23]
      : [22, 20, 21, 18, 19, 15, 16, 13, 14, 11, 10];

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;

  const padX = 4;
  const padY = 4;
  const w = width - padX * 2;
  const h = height - padY * 2;

  const pts = points.map((val, idx) => ({
    x: padX + (idx / (points.length - 1)) * w,
    y: padY + h - ((val - min) / range) * h,
  }));

  // Smooth spline curve (Cubic Bezier)
  let pathD = `M ${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = i > 0 ? pts[i - 1] : pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = i < pts.length - 2 ? pts[i + 2] : p2;

    const tension = 0.2;
    const cp1x = p1.x + (p2.x - p0.x) * tension;
    const cp1y = p1.y + (p2.y - p0.y) * tension;
    const cp2x = p2.x - (p3.x - p1.x) * tension;
    const cp2y = p2.y - (p3.y - p1.y) * tension;

    pathD += ` C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
  }

  const areaD = `${pathD} L ${padX + w},${padY + h} L ${padX},${padY + h} Z`;

  const colorStyles = {
    emerald: { stroke: '#10b981', fill: 'rgba(16, 185, 129, 0.25)' },
    cyan: { stroke: '#06b6d4', fill: 'rgba(6, 182, 212, 0.25)' },
    rose: { stroke: '#f43f5e', fill: 'rgba(244, 63, 94, 0.25)' },
    amber: { stroke: '#f59e0b', fill: 'rgba(245, 158, 11, 0.25)' },
    violet: { stroke: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.25)' },
  };

  const selectedColor = colorStyles[color];
  const lastPt = pts[pts.length - 1];

  return (
    <svg width={width} height={height} className="overflow-visible inline-block select-none">
      <defs>
        <linearGradient id={`sparkline-grad-${color}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={selectedColor.stroke} stopOpacity="0.35" />
          <stop offset="100%" stopColor={selectedColor.stroke} stopOpacity="0.0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill={`url(#sparkline-grad-${color})`} />
      <path
        d={pathD}
        fill="none"
        stroke={selectedColor.stroke}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Beacon tip */}
      <circle
        cx={lastPt.x}
        cy={lastPt.y}
        r="2.5"
        fill={selectedColor.stroke}
        className="animate-pulse"
      />
      <circle
        cx={lastPt.x}
        cy={lastPt.y}
        r="5"
        fill={selectedColor.stroke}
        opacity="0.3"
      />
    </svg>
  );
};

export default TrendSparkline;
