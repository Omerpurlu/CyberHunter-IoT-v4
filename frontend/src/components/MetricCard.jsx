import StatusBadge from './StatusBadge';

export default function MetricCard({
  title,
  value,
  description,
  icon,
  status,
  statusLabel,
  footer,
  className = '',
}) {
  return (
    <article className={`rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950/80 p-5 shadow-lg shadow-black/10 transition-colors duration-150 hover:border-slate-700 hover:bg-slate-900/80 ${className}`}>
      <div className="flex items-start justify-between gap-4">
        {icon && (
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-indigo-500/15 bg-indigo-500/10 text-indigo-300">
            {icon}
          </div>
        )}
        {status && <StatusBadge status={status} label={statusLabel} />}
      </div>
      <p className="mt-5 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
        {title}
      </p>
      <p className="mt-1 break-words text-2xl font-bold tracking-tight text-white">{value}</p>
      {description && <p className="mt-2 text-sm leading-5 text-slate-400">{description}</p>}
      {footer && <div className="mt-4 border-t border-slate-800 pt-4 text-sm text-slate-400">{footer}</div>}
    </article>
  );
}

