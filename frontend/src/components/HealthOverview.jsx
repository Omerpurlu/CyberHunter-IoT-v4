const flow = [
  { label: 'Raspberry Pi Bridge', color: 'text-rose-300', path: 'M7 7h10v10H7zM9 3v4m6-4v4' },
  { label: 'SDA/SCL', color: 'text-pink-300', path: 'M5 8h14M5 16h14' },
  { label: 'ESP32', color: 'text-blue-300', path: 'M7 7h10v10H7zM3 9h4m10 0h4' },
  { label: 'HTTPS/ngrok', color: 'text-violet-300', path: 'M8 11V8a4 4 0 118 0v3m-9 0h10v9H7z' },
  { label: 'FastAPI', color: 'text-indigo-300', path: 'M13 2L5 14h6l-1 8 9-13h-6z' },
  { label: 'PostgreSQL', color: 'text-cyan-300', path: 'M5 6c0-2 3-3 7-3s7 1 7 3-3 3-7 3-7-1-7-3z' },
  { label: 'Dashboard', color: 'text-purple-300', path: 'M4 5h16v12H4zM9 21h6' },
];

export default function HealthOverview({ apiAccessible, databaseAccessible }) {
  const servicesAccessible = apiAccessible && databaseAccessible;

  return (
    <section className="overflow-hidden rounded-[18px] border border-indigo-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/20 shadow-lg shadow-black/10">
      <div className="grid xl:grid-cols-[0.4fr_0.6fr] xl:items-stretch">
        <div className="flex items-center gap-4 border-b border-slate-800 p-5 sm:p-6 xl:border-b-0 xl:border-r">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-indigo-500/25 bg-indigo-500/10 text-indigo-300 shadow-lg shadow-indigo-950/20">
            <svg aria-hidden="true" className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M4 13h4l2-6 4 11 2-5h4M5 4h14v16H5z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-indigo-400">Genel Durum</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-white">Kısmen İzlenebilir</h2>
            <ul className="mt-3 space-y-1.5 text-sm text-slate-300">
              <li className="flex gap-2">
                <span aria-hidden="true" className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${servicesAccessible ? 'bg-emerald-400' : 'bg-red-400'}`} />
                FastAPI ve PostgreSQL sorgusu {servicesAccessible ? 'erişilebilir' : 'erişilemiyor'}
              </li>
              <li className="flex gap-2">
                <span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                Raspberry Pi ve ESP32 için heartbeat bekleniyor
              </li>
            </ul>
          </div>
        </div>

        <div className="min-w-0 p-5 sm:p-6">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Sistem Mimarisi</p>
          <div className="mt-3 overflow-x-auto pb-1">
            <div className="flex min-w-[650px] items-center">
              {flow.map((item, index) => (
                <div className="contents" key={item.label}>
                  <div className="flex min-w-0 flex-1 flex-col items-center gap-1.5 text-center">
                    <div className={`flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700 bg-slate-950/70 ${item.color}`}>
                      <svg aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" d={item.path} />
                      </svg>
                    </div>
                    <span className="text-[10px] font-semibold leading-tight text-slate-300">{item.label}</span>
                  </div>
                  {index < flow.length - 1 && (
                    <span aria-hidden="true" className="mx-1 -mt-5 text-sm text-slate-600">→</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

