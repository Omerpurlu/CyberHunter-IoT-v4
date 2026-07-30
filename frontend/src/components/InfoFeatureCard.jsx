export default function InfoFeatureCard({ eyebrow, title, icon, accent = 'indigo', children }) {
  const accents = {
    indigo: 'border-indigo-500/20 bg-indigo-500/10 text-indigo-300',
    rose: 'border-rose-500/20 bg-rose-500/10 text-rose-300',
    emerald: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
    cyan: 'border-cyan-500/20 bg-cyan-500/10 text-cyan-300',
  };

  return (
    <article className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950/70 p-5 shadow-lg shadow-black/10 transition-colors duration-150 hover:border-slate-700 sm:p-6">
      <div className={`flex h-11 w-11 items-center justify-center rounded-xl border ${accents[accent] || accents.indigo}`}>
        {icon}
      </div>
      {eyebrow && <p className="mt-5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">{eyebrow}</p>}
      <h2 className={`${eyebrow ? 'mt-1' : 'mt-5'} text-lg font-bold text-white`}>{title}</h2>
      <div className="mt-4 text-sm leading-6 text-slate-400">{children}</div>
    </article>
  );
}

