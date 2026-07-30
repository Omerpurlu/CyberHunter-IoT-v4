import StatusBadge from './StatusBadge';
import { tarihSaatFormatla } from '../utils/dateFormat';

function decisionStatus(decision) {
  const normalized = String(decision || '').toLowerCase();
  if (normalized === 'allow') return 'success';
  if (normalized === 'block') return 'error';
  if (normalized === 'warning' || normalized === 'warn') return 'warning';
  return 'unknown';
}

export default function SecurityEventList({ events, selectedId, highlightedIds, onSelect, rowRefs }) {
  return (
    <div className="space-y-3 md:hidden">
      {events.map(event => {
        const assessment = event.assessment;
        const selected = selectedId === event.event_id;
        return (
          <button
            type="button"
            key={event.event_id}
            ref={element => {
              if (element) rowRefs.current.set(event.event_id, element);
              else rowRefs.current.delete(event.event_id);
            }}
            aria-pressed={selected}
            onClick={() => onSelect(event)}
            className={`w-full rounded-2xl border bg-slate-900 p-4 text-left transition-colors duration-150 hover:bg-slate-800/80 ${
              selected ? 'border-indigo-500/50 bg-indigo-500/10' : 'border-slate-800'
            } ${highlightedIds.has(event.event_id) ? 'event-new-highlight' : ''}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-mono text-sm font-semibold text-slate-200">{event.source_ip || '—'}</p>
                <p className="mt-1 text-xs text-slate-400">{tarihSaatFormatla(event.event_timestamp)}</p>
              </div>
              <StatusBadge status={decisionStatus(assessment?.decision)} label={assessment?.decision || 'Değerlendirme yok'} />
            </div>
            <div className="mt-4 flex items-end justify-between gap-3 border-t border-slate-800 pt-3">
              <div>
                <p className="text-xs text-slate-400">Olay tipi</p>
                <p className="mt-1 text-sm font-medium text-slate-200">{event.event_type || '—'}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-400">ESP32 riski</p>
                <p className="mt-1 text-lg font-bold text-white">{assessment?.risk_score ?? '—'}</p>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

