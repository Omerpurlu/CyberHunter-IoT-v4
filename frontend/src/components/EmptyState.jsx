export default function EmptyState({ icon, title, description, action, className = '' }) {
  return (
    <section className={`flex min-h-64 flex-col items-center justify-center rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950/80 px-6 py-10 text-center shadow-lg shadow-black/10 ${className}`}>
      {icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-700 bg-slate-800/70 text-slate-300">
          {icon}
        </div>
      )}
      <h2 className="mt-4 text-lg font-bold text-white">{title}</h2>
      {description && <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </section>
  );
}
