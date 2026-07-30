import EmptyState from './EmptyState';
import ErrorState from './ErrorState';
import StatusBadge from './StatusBadge';
import { tarihSaatFormatla } from '../utils/dateFormat';
import { canliOzetiOlustur } from '../utils/securitySummary';

const summaryIcon = (
  <svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M4 7h16M4 12h10M4 17h7" />
  </svg>
);

export default function SystemLiveSummary({
  guvenlikOlaylari = [],
  sonDegerlendirmeOlayi,
  guvenlikOlaylariYukleniyor,
  guvenlikOlaylariHatasi,
}) {
  if (guvenlikOlaylariYukleniyor) {
    return (
      <EmptyState
        className="min-h-0 px-5 py-8 sm:px-6"
        icon={summaryIcon}
        title="Canlı özet yükleniyor"
        description="Güncel security-events verisi alınıyor."
      />
    );
  }

  if (guvenlikOlaylariHatasi) {
    return (
      <ErrorState
        className="min-h-0 px-5 py-8 sm:px-6"
        icon={summaryIcon}
        title="Canlı özet alınamadı"
        description={guvenlikOlaylariHatasi}
      />
    );
  }

  if (!guvenlikOlaylari.length) {
    return (
      <EmptyState
        className="min-h-0 px-5 py-8 sm:px-6"
        icon={summaryIcon}
        title="Henüz güvenlik olayı yok"
        description="İlk security event geldiğinde kısa sistem özeti burada gösterilecek."
      />
    );
  }

  const summary = canliOzetiOlustur(guvenlikOlaylari, sonDegerlendirmeOlayi);
  return (
    <article className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950/70 p-5 shadow-lg shadow-black/10 transition-colors duration-150 hover:border-slate-700 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-500/20 bg-cyan-500/10 text-cyan-300">
          {summaryIcon}
        </div>
        <StatusBadge status="success" label="Veri alındı" />
      </div>
      <h2 className="mt-5 text-lg font-bold text-white">Canlı Özet</h2>
      <dl className="mt-4 divide-y divide-slate-800 text-sm">
        <div className="flex items-center justify-between gap-4 py-2.5">
          <dt className="text-slate-400">Gösterilen olay</dt>
          <dd className="font-semibold text-white">{summary.gosterilenOlay}</dd>
        </div>
        <div className="flex items-center justify-between gap-4 py-2.5">
          <dt className="text-slate-400">Son olay zamanı</dt>
          <dd className="text-right font-semibold text-slate-200">{tarihSaatFormatla(summary.sonOlayZamani)}</dd>
        </div>
        <div className="flex items-center justify-between gap-4 py-2.5">
          <dt className="text-slate-400">Son ESP32 kararı</dt>
          <dd className="text-right font-semibold text-slate-200">{summary.sonKarar}</dd>
        </div>
        <div className="flex items-center justify-between gap-4 py-2.5">
          <dt className="text-slate-400">Veri durumu</dt>
          <dd className="font-semibold text-emerald-300">Güncel veri alındı</dd>
        </div>
      </dl>
    </article>
  );
}

