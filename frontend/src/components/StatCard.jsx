export default function StatCard({ kart }) {
  return (
    <article className={`rounded-2xl border ${kart.kenarlik} bg-gradient-to-br from-slate-950/80 to-slate-900/70 p-5 transition-colors duration-150 hover:border-slate-700 hover:bg-slate-900/80`}>
      <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${kart.ikonArkaPlan} ${kart.ikonRengi}`}>
        <svg aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d={kart.ikonYolu} />
        </svg>
      </div>
      <p className="mt-5 text-xs font-semibold uppercase tracking-wider text-slate-400">{kart.baslik}</p>
      <p className="mt-1 break-words text-2xl font-bold text-white">{kart.deger}</p>
      <p className="mt-2 text-sm leading-5 text-slate-400">{kart.aciklama}</p>
    </article>
  );
}
