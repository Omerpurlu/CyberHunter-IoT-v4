function RiskBar({ label, value, tone }) {
  const hasValue = value !== null && value !== undefined && value !== '';
  const number = hasValue ? Number(value) : null;
  const valid = Number.isFinite(number);
  const width = valid ? Math.min(100, Math.max(0, number)) : 0;

  return (
    <div>
      <div className="flex items-center justify-between gap-4 text-sm">
        <span className="text-slate-400">{label}</span>
        <span className="font-semibold text-slate-200">{valid ? number : 'Veri yok'}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

export default function RiskComparison({ inputRisk, esp32Risk }) {
  const inputNumber = Number(inputRisk);
  const esp32Number = Number(esp32Risk);
  const hasInput = inputRisk !== null && inputRisk !== undefined && inputRisk !== '' && Number.isFinite(inputNumber);
  const hasEsp32 = esp32Risk !== null && esp32Risk !== undefined && esp32Risk !== '' && Number.isFinite(esp32Number);
  const difference = hasInput && hasEsp32 ? esp32Number - inputNumber : null;

  return (
    <section className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950/70 p-5 shadow-lg shadow-black/10 sm:p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-400">Skor değişimi</p>
      <h2 className="mt-1 text-lg font-bold text-white">Risk Karşılaştırması</h2>
      <div className="mt-6 space-y-5">
        <RiskBar label="Raspberry Pi Girdi Riski" value={inputRisk} tone="bg-indigo-400" />
        <RiskBar label="ESP32 Riski" value={esp32Risk} tone="bg-emerald-400" />
      </div>
      <div className="mt-5 flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm">
        <span className="text-slate-400">Aradaki fark</span>
        <strong className="text-white">{difference === null ? 'Veri yok' : difference > 0 ? `+${difference}` : difference}</strong>
      </div>
    </section>
  );
}

