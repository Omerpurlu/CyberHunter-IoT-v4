export default function ErrorState({ icon, title, description, action, className = '' }) {
  return (
    <section
      role="alert"
      className={`flex min-h-64 flex-col items-center justify-center rounded-3xl border border-red-500/20 bg-gradient-to-br from-slate-900 to-red-950/10 px-6 py-10 text-center shadow-lg shadow-black/10 ${className}`}
    >
      {icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-red-500/20 bg-red-500/10 text-red-300">
          {icon}
        </div>
      )}
      <h2 className="mt-4 text-lg font-bold text-red-200">{title}</h2>
      {description && <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </section>
  );
}

