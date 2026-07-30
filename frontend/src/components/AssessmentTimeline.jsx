import { tarihSaatFormatla } from '../utils/dateFormat';

export default function AssessmentTimeline({ event, assessment }) {
  const items = [
    ['Olay zamanı', event?.event_timestamp],
    ["Backend'e alınma zamanı", event?.received_at],
    ['Assessment zamanı', assessment?.assessed_at],
    ['Assessment alınma zamanı', assessment?.received_at],
  ];

  return (
    <section className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950/70 p-5 shadow-lg shadow-black/10 sm:p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-400">İşlem sırası</p>
      <h2 className="mt-1 text-lg font-bold text-white">Zaman Bilgileri</h2>
      <ol className="mt-5 space-y-4">
        {items.map(([label, value], index) => (
          <li className="relative flex gap-3" key={label}>
            <div className="flex flex-col items-center">
              <span className="mt-1.5 h-2.5 w-2.5 rounded-full border-2 border-indigo-300 bg-indigo-500/20" />
              {index < items.length - 1 && <span aria-hidden="true" className="mt-1 h-full min-h-8 w-px bg-slate-700" />}
            </div>
            <div className="pb-1">
              <p className="text-xs font-medium text-slate-400">{label}</p>
              <p className="mt-1 text-sm font-semibold text-slate-200">{tarihSaatFormatla(value)}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

