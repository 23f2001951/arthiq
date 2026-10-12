import React, { useEffect, useState } from 'react';
import { CalendarClock, RefreshCw, Radio, TriangleAlert } from 'lucide-react';
import { fetchCorporateEvents } from '../api/client';
import { CorporateEventItem } from '../types/api';

interface EdgeViewProps {
  asof: string;
}

export const EdgeView: React.FC<EdgeViewProps> = ({ asof }) => {
  const [events, setEvents] = useState<CorporateEventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchCorporateEvents(asof);
      setEvents(response.events || []);
    } catch (err: any) {
      setError(err.message || 'Unable to load corporate events.');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadEvents(); }, [asof]);

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-winsor-300 font-semibold">Point-in-time event feed</p>
          <h2 className="mt-1 text-xl font-semibold text-white">Corporate events</h2>
          <p className="mt-1 text-xs text-slate-400">Events visible at the selected cutoff date · {asof}</p>
        </div>
        <button onClick={() => void loadEvents()} disabled={loading} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-white/10 text-xs text-slate-300 hover:text-white disabled:opacity-50">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && <div className="p-4 rounded-2xl border border-rose-500/20 bg-rose-950/20 text-sm text-rose-200">{error}</div>}

      {loading ? (
        <div className="glass-card min-h-48 rounded-2xl flex items-center justify-center gap-3 text-sm text-slate-400">
          <RefreshCw className="w-4 h-4 animate-spin" /> Loading point-in-time events…
        </div>
      ) : !error && events.length === 0 ? (
        <div className="glass-card min-h-48 rounded-2xl p-8 flex flex-col items-center justify-center text-center">
          <CalendarClock className="w-6 h-6 text-slate-500 mb-3" />
          <h3 className="text-sm font-semibold text-white">No events for this cutoff</h3>
          <p className="mt-1 max-w-md text-xs leading-relaxed text-slate-400">The event feed has no stored corporate disclosures for the selected date window. No sample events are substituted.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {events.map((event) => {
            const direction = event.direction.toLowerCase();
            const tone = direction.includes('positive') || direction.includes('bull') ? 'text-emerald-300 border-emerald-500/20 bg-emerald-950/20'
              : direction.includes('negative') || direction.includes('bear') ? 'text-rose-300 border-rose-500/20 bg-rose-950/20'
              : 'text-slate-300 border-white/10 bg-white/[0.03]';
            return (
              <article key={event.event_id} className="glass-card rounded-2xl p-4 sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-bold text-white">{event.symbol}</span>
                      <span className="px-2 py-0.5 rounded-full border border-white/10 text-[9px] uppercase tracking-wider text-slate-400">{event.event_type.replace(/_/g, ' ')}</span>
                      <span className={`px-2 py-0.5 rounded-full border text-[9px] uppercase tracking-wider ${tone}`}>{event.direction}</span>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-slate-200">{event.headline}</p>
                  </div>
                  <div className="shrink-0 text-right text-[10px] font-mono text-slate-400">
                    <div>{event.effective_date}</div>
                    <div className="mt-1">Materiality {event.materiality_score.toFixed(1)}</div>
                    <div>Confidence {event.confidence_score.toFixed(1)}</div>
                  </div>
                </div>
                {event.affected_factors.length > 0 && <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  <TriangleAlert className="w-3 h-3 text-winsor-300" />
                  {event.affected_factors.map((factor) => <span key={factor} className="px-2 py-0.5 rounded-md bg-white/[0.04] text-[10px] text-slate-400">{factor.replace(/_/g, ' ')}</span>)}
                </div>}
              </article>
            );
          })}
        </div>
      )}
      <p className="flex items-center gap-1.5 text-[10px] text-slate-500"><Radio className="w-3 h-3" /> Events are point-in-time records; this view does not claim a real-time news stream.</p>
    </section>
  );
};
