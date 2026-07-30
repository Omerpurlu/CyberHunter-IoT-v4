export default function PageHeader({ eyebrow, title, description, actions, meta }) {
  return (
    <header className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg shadow-black/10 sm:p-6 lg:p-7">
      <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          {eyebrow && (
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-400">
              {eyebrow}
            </p>
          )}
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            {title}
          </h1>
          {description && (
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
              {description}
            </p>
          )}
        </div>
        {(actions || meta) && (
          <div className="flex shrink-0 flex-col items-start gap-3 md:items-end">
            {actions}
            {meta}
          </div>
        )}
      </div>
    </header>
  );
}

