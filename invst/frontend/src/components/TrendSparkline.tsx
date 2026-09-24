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
  width = 90,
  height = 28,
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

  const pad = 2;
  const w = width - pad * 2;
  const h = height - pad * 2;

  const coords = points.map((val, idx) => {
    const x = pad + (idx / (points.length - 1)) * w;
    const y = pad + h - ((val - min) / range) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const pathD = `M ${coords.join(' L ')}`;
  const areaD = `${pathD} L ${pad + w},${pad + h} L ${pad},${pad + h} Z`;

  const colorStyles = {
    emerald: { stroke: '#10b981', fill: 'rgba(16, 185, 129, 0.15)' },
    cyan: { stroke: '#06b6d4', fill: 'rgba(6, 182, 212, 0.15)' },
    rose: { stroke: '#f43f5e', fill: 'rgba(244, 63, 94, 0.15)' },
    amber: { stroke: '#f59e0b', fill: 'rgba(245, 158, 11, 0.15)' },
    violet: { stroke: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.15)' },
  };

  const selectedColor = colorStyles[color];

  return (
    <svg width={width} height={height} className="overflow-visible inline-block">
      <defs>
        <linearGradient id={`sparkline-grad-${color}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={selectedColor.stroke} stopOpacity="0.25" />
          <stop offset="100%" stopColor={selectedColor.stroke} stopOpacity="0.0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill={`url(#sparkline-grad-${color})`} />
      <path d={pathD} fill="none" stroke={selectedColor.stroke} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
      <circle
        cx={coords[coords.length - 1].split(',')[0]}
        cy={coords[coords.length - 1].split(',')[1]}
        r="2"
        fill={selectedColor.stroke}
      />
    </svg>
  );
};
