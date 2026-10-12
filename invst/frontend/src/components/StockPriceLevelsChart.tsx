import React, { useMemo, useState } from 'react';
import { Activity, CalendarDays } from 'lucide-react';

export interface StockPricePoint {
  date: string;
  close: number;
}

interface StockPriceLevelsChartProps {
  symbol: string;
  points: StockPricePoint[];
  asofDate?: string | null;
  quoteAsOf?: string | null;
  currentPrice: number;
  low52w: number;
  high52w: number;
  dma50?: number;
  dma200?: number;
  dipTargetPrice?: number;
  isLive?: boolean;
  period: '1D' | '30D' | '6M' | '1Y';
  onPeriodChange: (period: '1D' | '30D' | '6M' | '1Y') => void;
}

const fmtPrice = (value: number) => `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 1 })}`;

export const StockPriceLevelsChart: React.FC<StockPriceLevelsChartProps> = ({
  symbol, points, asofDate, quoteAsOf, currentPrice, low52w, high52w, dma50, dma200, dipTargetPrice, isLive, period, onPeriodChange,
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const width = 1000;
  const height = 360;
  const pad = { top: 24, right: 190, bottom: 42, left: 72 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const levels = [
    { key: '52w-low', label: '52W Low', value: low52w, color: '#849278', dash: '4 5' },
    ...(dipTargetPrice && dipTargetPrice > 0 ? [{ key: 'dip', label: 'Dip target', value: dipTargetPrice, color: '#248260', dash: '5 4' }] : []),
    ...(dma50 && dma50 > 0 ? [{ key: 'dma50', label: '50-DMA', value: dma50, color: '#3f9297', dash: '6 4' }] : []),
    ...(dma200 && dma200 > 0 ? [{ key: 'dma200', label: '200-DMA', value: dma200, color: '#806ca1', dash: '6 4' }] : []),
    { key: 'cmp', label: isLive ? 'Live CMP' : 'Latest CMP', value: currentPrice, color: '#a17d35', dash: '0' },
    { key: '52w-high', label: '52W High', value: high52w, color: '#9b7770', dash: '4 5' },
  ].filter((level) => Number.isFinite(level.value) && level.value > 0);

  const chart = useMemo(() => {
    if (points.length < 2) return null;
    const dataValues = points.map((point) => point.close).filter(Number.isFinite);
    const dataMin = Math.min(...dataValues);
    const dataMax = Math.max(...dataValues);
    const dataSpan = dataMax - dataMin || dataMax * 0.02 || 1;
    // Levels outside the selected chart's visible price band must not distort
    // the historical price scale (especially 52-week levels on a 1D view).
    const visibleLevels = levels.filter((level) => level.value >= dataMin - dataSpan * 0.16 && level.value <= dataMax + dataSpan * 0.16);
    const values = [...dataValues, ...visibleLevels.map((level) => level.value)];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || max * 0.05 || 1;
    const floor = min - span * 0.08;
    const ceil = max + span * 0.08;
    const x = (index: number) => pad.left + (index / (points.length - 1)) * plotWidth;
    const y = (value: number) => pad.top + ((ceil - value) / (ceil - floor)) * plotHeight;
    const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index).toFixed(1)} ${y(point.close).toFixed(1)}`).join(' ');
    const area = `${path} L ${x(points.length - 1).toFixed(1)} ${(pad.top + plotHeight).toFixed(1)} L ${x(0).toFixed(1)} ${(pad.top + plotHeight).toFixed(1)} Z`;
    return { min: floor, max: ceil, x, y, path, area, visibleLevels };
  }, [points, levels, pad.left, pad.top, plotHeight, plotWidth]);

  const activePoint = hoverIndex === null ? null : points[hoverIndex];
  const activeX = chart && hoverIndex !== null ? chart.x(hoverIndex) : null;
  const dateLabel = (value?: string | null) => value ? new Date(value.length === 10 ? `${value}T00:00:00` : value).toLocaleString('en-IN', period === '1D' ? { hour: '2-digit', minute: '2-digit' } : { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
  const levelLabelY = new Map<string, number>();
  if (chart) {
    const ordered = chart.visibleLevels.map((level) => ({ level, y: chart.y(level.value) })).sort((a, b) => a.y - b.y);
    ordered.forEach(({ level, y }, index) => {
      let displayY = Math.max(pad.top + 10, Math.min(pad.top + plotHeight - 10, y));
      if (index > 0) {
        const previous = ordered[index - 1];
        displayY = Math.max(displayY, (levelLabelY.get(previous.level.key) || previous.y) + 22);
      }
      levelLabelY.set(level.key, Math.min(pad.top + plotHeight - 10, displayY));
    });
  }

  return (
    <section className="stock-price-chart workspace-feature-panel" aria-label={`${symbol} price history and key levels`}>
      <div className="stock-price-chart__header">
        <div className="flex items-start gap-3">
          <span className="stock-price-chart__icon"><Activity className="w-4 h-4" /></span>
          <div>
            <h3>Price history &amp; key levels</h3>
            <p>Daily closes from stored market history, with decision levels plotted on the same price scale.</p>
          </div>
        </div>
        <div className="stock-price-chart__meta">
          <div className="stock-price-chart__ranges" role="group" aria-label="Price history range">
            {(['1D', '30D', '6M', '1Y'] as const).map((range) => <button key={range} type="button" onClick={() => onPeriodChange(range)} className={period === range ? 'is-active' : ''}>{range}</button>)}
          </div>
          <span className="stock-price-chart__asof"><CalendarDays className="w-3.5 h-3.5" /> {period === '1D' ? 'Intraday' : 'Daily'} history as of {dateLabel(asofDate)}</span>
        </div>
      </div>

      {chart ? (
        <div className="stock-price-chart__plot-wrap">
          <div className="stock-price-chart__readout">
            <span>{dateLabel(activePoint?.date || quoteAsOf || asofDate)}</span>
            <strong>{activePoint ? fmtPrice(activePoint.close) : fmtPrice(currentPrice)}</strong>
            {hoverIndex === null && <span className="stock-price-chart__source">{isLive ? 'Live quote' : 'Latest quote'}</span>}
          </div>
          <svg className="stock-price-chart__svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${symbol} historical closing price chart with key price levels`} onMouseLeave={() => setHoverIndex(null)}>
            <defs>
              <linearGradient id="stock-area-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#527b62" stopOpacity="0.22" />
                <stop offset="100%" stopColor="#527b62" stopOpacity="0.015" />
              </linearGradient>
            </defs>
            {[0, 1, 2, 3, 4].map((step) => {
              const value = chart.max - ((chart.max - chart.min) * step) / 4;
              const y = pad.top + (plotHeight * step) / 4;
              return <g key={step}><line x1={pad.left} x2={width - pad.right} y1={y} y2={y} className="stock-chart-grid" /><text x={pad.left - 12} y={y + 4} textAnchor="end" className="stock-chart-axis">{Math.round(value).toLocaleString('en-IN')}</text></g>;
            })}
            <path d={chart.area} fill="url(#stock-area-fill)" />
            {chart.visibleLevels.map((level) => {
              const y = chart.y(level.value);
              return <g key={level.key}>
                <line x1={pad.left} x2={width - pad.right + 5} y1={y} y2={y} stroke={level.color} strokeWidth={level.key === 'cmp' ? 1.8 : 1.25} strokeDasharray={level.dash} opacity={level.key === 'cmp' ? 0.95 : 0.76} />
                <rect x={width - pad.right + 12} y={(levelLabelY.get(level.key) || y) - 10} width={pad.right - 24} height="20" rx="6" fill="var(--chart-label-bg)" stroke={level.color} strokeOpacity="0.35" />
                <text x={width - pad.right + 20} y={(levelLabelY.get(level.key) || y) + 3.5} className="stock-chart-level-label" fill={level.color}>{level.label}</text>
                <text x={width - 12} y={(levelLabelY.get(level.key) || y) + 3.5} textAnchor="end" className="stock-chart-level-value">{fmtPrice(level.value)}</text>
              </g>;
            })}
            <path d={chart.path} fill="none" stroke="#39765a" strokeWidth="2.7" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
            {activeX !== null && activePoint && <g><line x1={activeX} x2={activeX} y1={pad.top} y2={pad.top + plotHeight} className="stock-chart-crosshair" /><circle cx={activeX} cy={chart.y(activePoint.close)} r="4.5" fill="#39765a" stroke="var(--chart-label-bg)" strokeWidth="2" /></g>}
            <rect x={pad.left} y={pad.top} width={plotWidth} height={plotHeight} fill="transparent" onMouseMove={(event) => {
              const bounds = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
              if (!bounds) return;
              const localX = ((event.clientX - bounds.left) / bounds.width) * width - pad.left;
              setHoverIndex(Math.max(0, Math.min(points.length - 1, Math.round((localX / plotWidth) * (points.length - 1)))));
            }} />
            {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
              const index = Math.round((points.length - 1) * ratio);
              return <text key={ratio} x={chart.x(index)} y={height - 12} textAnchor={ratio === 0 ? 'start' : ratio === 1 ? 'end' : 'middle'} className="stock-chart-axis">{dateLabel(points[index]?.date)}</text>;
            })}
          </svg>
        </div>
      ) : (
        <div className="stock-price-chart__empty">{period === '1D' ? 'No stored intraday candles are available for this symbol. Choose 30D, 6M, or 1Y to view stored daily prices.' : 'No stored daily price series is available for this symbol and range. Analysis key levels remain based on the stock analysis response.'}</div>
      )}

    </section>
  );
};

export default StockPriceLevelsChart;
