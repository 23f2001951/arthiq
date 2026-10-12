import React, { useEffect, useMemo, useState } from 'react';
import { fetchStockPriceHistory } from '../api/client';
import { StockPricePoint } from './StockPriceLevelsChart';

type Range = '1D' | '30D' | '6M' | '1Y';
const formatPrice = (price: number) => `₹${price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

interface MarketBenchmarkPanelProps {
  liveQuote?: number | null;
  liveAsOf?: string | null;
}

export const MarketBenchmarkPanel: React.FC<MarketBenchmarkPanelProps> = ({ liveQuote, liveAsOf }) => {
  const [range, setRange] = useState<Range>('1Y');
  const [points, setPoints] = useState<StockPricePoint[]>([]);
  const [asof, setAsof] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchStockPriceHistory('NIFTY50', range).then((history) => {
      if (cancelled) return;
      setPoints(history.points || []);
      setAsof(history.asof_date);
    }).catch(() => {
      if (!cancelled) { setPoints([]); setAsof(null); }
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [range]);

  const chart = useMemo(() => {
    if (points.length < 2) return null;
    const width = 760, height = 240, left = 54, right = 12, top = 12, bottom = 24;
    const vals = points.map((point) => point.close);
    const min = Math.min(...vals), max = Math.max(...vals);
    const pad = (max - min || max * .02 || 1) * .08;
    const lo = min - pad, hi = max + pad;
    const x = (index: number) => left + (index / (points.length - 1)) * (width - left - right);
    const y = (value: number) => top + ((hi - value) / (hi - lo)) * (height - top - bottom);
    const line = points.map((point, index) => `${index ? 'L' : 'M'} ${x(index).toFixed(1)} ${y(point.close).toFixed(1)}`).join(' ');
    const area = `${line} L ${x(points.length - 1)} ${height - bottom} L ${x(0)} ${height - bottom} Z`;
    return { width, height, left, right, top, bottom, min: lo, max: hi, x, line, area };
  }, [points]);

  const move = points.length > 1 ? ((points[points.length - 1].close / points[0].close) - 1) * 100 : null;
  const dateLabel = (value: string | null) => value ? new Date(value.length === 10 ? `${value}T00:00:00` : value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

  return <section className="market-benchmark-panel">
    <div className="market-benchmark-panel__intro">
      <div><span className="market-section-kicker">MARKET OVERVIEW</span><h2>NIFTY 50</h2><p>Stored index price history · range change is calculated from displayed observations</p></div>
      <div className="market-benchmark-panel__latest">{points.length > 0 ? <><strong>{formatPrice(points[points.length - 1].close)}</strong><span>Latest stored close · {dateLabel(asof)}</span></> : Number.isFinite(liveQuote) && Number(liveQuote) > 0 ? <><strong>{formatPrice(Number(liveQuote))}</strong><span>Live NIFTY 50 quote · {dateLabel(liveAsOf || null)}</span></> : <><strong>—</strong><span>Stored index close unavailable</span></>}</div>
    </div>
    <div className="market-benchmark-panel__toolbar">
      <div className="market-benchmark-panel__ranges" role="group" aria-label="NIFTY 50 chart range">{(['1D', '30D', '6M', '1Y'] as const).map((item) => <button type="button" key={item} onClick={() => setRange(item)} className={range === item ? 'is-active' : ''}>{item}</button>)}</div>
      {move !== null && <span className={`market-benchmark-panel__move ${move >= 0 ? 'is-up' : 'is-down'}`}>{move >= 0 ? '+' : ''}{move.toFixed(2)}% <small>over {range}</small></span>}
    </div>
    {chart ? <svg className="market-benchmark-panel__chart" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label={`NIFTY 50 ${range} stored closing price trend`}>
      <defs><linearGradient id="market-index-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#54704c" stopOpacity=".18"/><stop offset="100%" stopColor="#54704c" stopOpacity="0"/></linearGradient></defs>
      {[0,1,2,3].map((i) => { const y = chart.top + i * ((chart.height - chart.top - chart.bottom) / 3); const value = chart.max - i * ((chart.max - chart.min) / 3); return <g key={i}><line x1={chart.left} x2={chart.width - chart.right} y1={y} y2={y} className="market-benchmark-panel__grid"/><text x={chart.left - 8} y={y + 4} textAnchor="end" className="market-benchmark-panel__axis">{Math.round(value).toLocaleString('en-IN')}</text></g>; })}
      <path d={chart.area} fill="url(#market-index-area)"/><path d={chart.line} fill="none" stroke="#496c4a" strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke"/>
      {[0,.33,.66,1].map((ratio) => { const index = Math.round((points.length - 1) * ratio); return <text key={ratio} x={chart.x(index)} y={chart.height - 5} textAnchor={ratio === 0 ? 'start' : ratio === 1 ? 'end' : 'middle'} className="market-benchmark-panel__axis">{dateLabel(points[index]?.date || null)}</text>; })}
    </svg> : <div className="market-benchmark-panel__empty"><strong>{loading ? 'Loading stored market history…' : range === '1D' ? 'Intraday history isn’t available yet' : 'NIFTY 50 history isn’t available for this range'}</strong><span>{range === '1D' ? 'Choose 30D, 6M, or 1Y to view stored daily closes.' : 'The current quote is shown above; no price line is drawn until historical observations are available.'}</span></div>}
    <div className="market-benchmark-panel__footnote">{range === '1D' ? '15-minute stored candles' : 'Daily stored closes'} · as of {dateLabel(asof)} · no illustrative prices</div>
  </section>;
};
