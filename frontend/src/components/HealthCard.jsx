import StatusBadge from './StatusBadge';
import { tarihSaatFormatla } from '../utils/dateFormat';

const iconTones = {
  amber: 'border-amber-500/20 bg-amber-500/10 text-amber-300',
  blue: 'border-blue-500/20 bg-blue-500/10 text-blue-300',
  emerald: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
  teal: 'border-teal-500/20 bg-teal-500/10 text-teal-300',
  purple: 'border-purple-500/20 bg-purple-500/10 text-purple-300',
};

export default function HealthCard({
  name,
  role,
  status,
  statusLabel,
  timeLabel,
  time,
  emptyTimeText,
  source,
  description,
  error,
  pulse = false,
  className = '',
  icon,
  iconTone = 'blue',
}) {
  const formattedTime = tarihSaatFormatla(time);
  const displayedTime = formattedTime === 'Veri yok' && emptyTimeText ? emptyTimeText : formattedTime;

  return (
    <article className={`min-w-0 rounded-[18px] border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950/75 p-5 shadow-lg shadow-black/10 transition-colors duration-150 hover:border-slate-700 hover:bg-slate-900/85 sm:p-6 ${className}`}>
      <div className="flex min-w-0 items-start gap-4">
        <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full border ${iconTones[iconTone] || iconTones.blue}`}>
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-bold text-white">{name}</h3>
          <p className="mt-0.5 text-sm leading-5 text-slate-400">{role}</p>
          <div className="mt-2.5">
            <StatusBadge status={status} label={statusLabel} pulse={pulse} />
          </div>
        </div>
      </div>

      <dl className="mt-5 space-y-3 border-t border-slate-800 pt-4 text-sm">
        <div className="flex items-start justify-between gap-4">
          <dt className="shrink-0 text-slate-400">{timeLabel}</dt>
          <dd className="text-right font-semibold text-slate-200">{displayedTime}</dd>
        </div>
        <div className="flex items-start justify-between gap-4">
          <dt className="shrink-0 text-slate-400">Kaynak</dt>
          <dd className="text-right font-medium text-slate-300">{source}</dd>
        </div>
      </dl>

      {description && (
        <p className="mt-4 rounded-xl border border-slate-800 bg-slate-950/50 px-3.5 py-3 text-xs leading-5 text-slate-400">
          {description}
        </p>
      )}

      {error && (
        <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/5 px-3.5 py-3">
          <p className="text-xs font-semibold text-red-300">Son hata</p>
          <p className="mt-1 break-words text-xs leading-5 text-red-200">{error}</p>
        </div>
      )}
    </article>
  );
}
