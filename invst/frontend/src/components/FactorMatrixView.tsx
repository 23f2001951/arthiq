import React, { useMemo, useState } from 'react';
import { ArrowUpDown, ArrowUpRight, ChevronUp, Eye } from 'lucide-react';
import { StockRecommendationItem } from '../types/api';
import { TrendSparkline } from './TrendSparkline';

interface FactorMatrixViewProps { stocks: StockRecommendationItem[]; onAnalyze?: (symbol: string) => void; }
type SortField = 'score' | 'price' | 'return' | 'quality' | 'valuation';
type VerdictFilter = 'ALL' | 'INVEST' | 'WAIT' | 'REJECT';

const verdictFor = (action: string) => {
  const normalized = action.toUpperCase();
  if (normalized === 'BUY' || normalized === 'INVEST') return 'INVEST';
  if (normalized === 'HOLD' || normalized === 'WAIT') return 'WAIT';
  return 'REJECT';
};
const money = (value?: number | null) => value == null ? '—' : `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

export const FactorMatrixView: React.FC<FactorMatrixViewProps> = ({ stocks, onAnalyze }) => {
  const [sortField, setSortField] = useState<SortField>('score');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>('ALL');
  const sortedStocks = useMemo(() => [...stocks].sort((a, b) => {
    if (sortField === 'quality') return b.quality_score - a.quality_score;
    if (sortField === 'valuation') return b.valuation_score - a.valuation_score;
    if (sortField === 'price') return (b.latest_close ?? -Infinity) - (a.latest_close ?? -Infinity);
    if (sortField === 'return') return (b.one_year_return_pct ?? -Infinity) - (a.one_year_return_pct ?? -Infinity);
    return (b.arth_score ?? b.composite_score * 100) - (a.arth_score ?? a.composite_score * 100);
  }), [stocks, sortField]);
  const visibleStocks = sortedStocks.filter((stock) => verdictFilter === 'ALL' || verdictFor(stock.action) === verdictFilter);

  return <section className="ideas-table-panel">
    <div className="ideas-table-panel__header"><div><span className="market-section-kicker">POINT-IN-TIME RESEARCH</span><h2>Investment ideas</h2><p>Current price and one-year return are calculated from stored closes available at the selected date.</p></div>
      <label className="ideas-table-panel__sort"><ArrowUpDown size={14}/><span>Sort</span><select aria-label="Sort investment ideas" value={sortField} onChange={(event) => setSortField(event.target.value as SortField)}><option value="score">Arth IQ score</option><option value="return">1Y return</option><option value="price">Latest close</option><option value="quality">Quality</option><option value="valuation">Valuation</option></select></label>
    </div>
    <div className="ideas-table-panel__filters">{(['ALL', 'INVEST', 'WAIT', 'REJECT'] as const).map((filter) => <button type="button" key={filter} onClick={() => setVerdictFilter(filter)} className={verdictFilter === filter ? 'is-active' : ''}>{filter === 'ALL' ? 'All ideas' : filter[0] + filter.slice(1).toLowerCase()} <b>{filter === 'ALL' ? stocks.length : stocks.filter((stock) => verdictFor(stock.action) === filter).length}</b></button>)}</div>
    <div className="ideas-table-panel__scroll"><table className="ideas-table"><thead><tr><th>Company</th><th className="is-center">Arth IQ score</th><th>Verdict</th><th>Key reasons</th><th className="is-right">Latest close</th><th className="is-right">1Y return</th><th>30D trend</th><th className="is-right">Actions</th></tr></thead><tbody>
      {visibleStocks.map((stock) => {
        const score = stock.arth_score ?? stock.composite_score * 100;
        const verdict = verdictFor(stock.action);
        const isExpanded = expanded === stock.symbol;
        return <React.Fragment key={stock.symbol}><tr className="ideas-table__row">
          <td><strong>{stock.symbol}</strong><small>{stock.sector.replace(/_/g, ' ')}</small></td>
          <td className="is-center"><span className={`ideas-score ${score >= 75 ? 'is-high' : score < 50 ? 'is-low' : ''}`}>{score.toFixed(0)}</span></td>
          <td><span className={`ideas-verdict is-${verdict.toLowerCase()}`}>{verdict}</span>{stock.alpha_model_available && stock.p_outperform != null && <small className="ideas-table__confidence">{Math.round(stock.p_outperform * 100)}% model probability</small>}</td>
          <td><p className="ideas-table__reason" title={stock.rationale}>{stock.rationale || 'No rationale supplied.'}</p></td>
          <td className="is-right ideas-table__number">{money(stock.latest_close)}</td>
          <td className={`is-right ideas-table__number ${stock.one_year_return_pct == null ? '' : stock.one_year_return_pct >= 0 ? 'is-positive' : 'is-negative'}`}>{stock.one_year_return_pct == null ? '—' : `${stock.one_year_return_pct >= 0 ? '+' : ''}${stock.one_year_return_pct.toFixed(1)}%`}</td>
          <td><TrendSparkline data={stock.price_trend} width={76} height={26} color={(stock.price_trend?.[Math.max(0, (stock.price_trend?.length ?? 1) - 1)] ?? 0) >= (stock.price_trend?.[0] ?? 0) ? 'emerald' : 'rose'} /></td>
          <td className="is-right"><span className="ideas-table__actions"><button className="ideas-table__detail-button" onClick={() => setExpanded(isExpanded ? null : stock.symbol)} aria-label={`${isExpanded ? 'Hide' : 'Show'} ${stock.symbol} factor detail`}>{isExpanded ? <ChevronUp size={15}/> : <Eye size={15}/>}</button>{onAnalyze && <button className="ideas-table__detail-button" onClick={() => onAnalyze(stock.symbol)} aria-label={`Open ${stock.symbol} in stock analyzer`}><ArrowUpRight size={15}/></button>}</span></td>
        </tr>{isExpanded && <tr className="ideas-table__expanded"><td colSpan={8}><div className="ideas-factor-bars">{[['Business quality', stock.quality_score], ['Valuation', stock.valuation_score], ['Risk', stock.risk_score]].map(([label, scoreValue]) => <div key={String(label)}><span>{label}</span><div><i style={{ width: `${Math.max(0, Math.min(100, Number(scoreValue) * 100))}%` }}/></div><strong>{(Number(scoreValue) * 100).toFixed(0)}</strong></div>)}</div><p>{stock.rationale}</p></td></tr>}</React.Fragment>;
      })}
    </tbody></table></div>
    {visibleStocks.length === 0 && <div className="ideas-table-panel__empty">No recommendations match this point-in-time selection.</div>}
  </section>;
};
