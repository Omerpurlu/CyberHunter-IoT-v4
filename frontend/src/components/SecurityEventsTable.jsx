import StatusBadge from './StatusBadge';
import { tarihSaatFormatla } from '../utils/dateFormat';

function decisionStatus(decision) {
  const normalized = String(decision || '').toLowerCase();
  if (normalized === 'allow') return 'success';
  if (normalized === 'block') return 'error';
  if (normalized === 'warning' || normalized === 'warn') return 'warning';
  return 'unknown';
}

export default function SecurityEventsTable({ events, selectedId, highlightedIds, onSelect, rowRefs }) {
  return (
    <div className="hidden overflow-x-auto rounded-3xl border border-slate-800 bg-slate-950/70 shadow-lg shadow-black/10 md:block">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead className="bg-slate-900/95 text-xs uppercase tracking-[0.12em] text-slate-400">
          <tr>
            {['Zaman', 'Kaynak IP', 'Olay tipi', 'Protokol', 'Girdi riski', 'ESP32 riski', 'Karar'].map(title => (
              <th className="px-4 py-3.5 font-semibold" key={title}>{title}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {events.map(event => {
            const assessment = event.assessment;
            const selected = selectedId === event.event_id;
            return (
              <tr
                key={event.event_id}
                ref={element => {
                  if (element) rowRefs.current.set(event.event_id, element);
                  else rowRefs.current.delete(event.event_id);
                }}
                tabIndex={0}
                aria-selected={selected}
                onClick={() => onSelect(event)}
                onKeyDown={keyboardEvent => {
                  if (keyboardEvent.key === 'Enter' || keyboardEvent.key === ' ') {
                    keyboardEvent.preventDefault();
                    onSelect(event);
                  }
                }}
                className={`cursor-pointer outline-none transition-colors duration-150 hover:bg-slate-800/55 focus-visible:bg-slate-800/60 ${
                  selected ? 'bg-indigo-500/10 ring-1 ring-inset ring-indigo-500/35' : ''
                } ${highlightedIds.has(event.event_id) ? 'event-new-highlight' : ''}`}
              >
                <td className="whitespace-nowrap px-4 py-3.5 text-slate-400">{tarihSaatFormatla(event.event_timestamp)}</td>
                <td className="whitespace-nowrap px-4 py-3.5 font-mono text-slate-200">{event.source_ip || '—'}</td>
                <td className="px-4 py-3.5 text-slate-200">{event.event_type || '—'}</td>
                <td className="px-4 py-3.5 text-slate-300">{event.protocol || '—'}</td>
                <td className="px-4 py-3.5 font-semibold text-slate-200">{event.input_risk_score ?? '—'}</td>
                <td className="px-4 py-3.5 font-semibold text-slate-200">{assessment?.risk_score ?? '—'}</td>
                <td className="px-4 py-3.5">
                  <StatusBadge status={decisionStatus(assessment?.decision)} label={assessment?.decision || 'Değerlendirme yok'} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

