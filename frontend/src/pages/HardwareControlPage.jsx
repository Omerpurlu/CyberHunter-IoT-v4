import AssessmentTimeline from '../components/AssessmentTimeline';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import PageHeader from '../components/PageHeader';
import RiskComparison from '../components/RiskComparison';
import RiskGauge from '../components/RiskGauge';
import StatusBadge from '../components/StatusBadge';
import { tarihSaatFormatla } from '../utils/dateFormat';

function decisionAppearance(decision) {
  const normalized = String(decision || '').toLowerCase();
  if (normalized === 'allow') return { status: 'success', explanation: 'İzin verildi' };
  if (normalized === 'block') return { status: 'error', explanation: 'Engellendi' };
  if (normalized === 'warning' || normalized === 'warn') return { status: 'warning', explanation: 'Uyarı' };
  return { status: 'unknown', explanation: 'Tanımlanmamış karar' };
}

function Detail({ label, value, mono = false, title }) {
  const displayed = value === null || value === undefined || value === '' ? 'Veri yok' : value;
  return (
    <div className="min-w-0 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <dt className="text-xs font-medium text-slate-400">{label}</dt>
      <dd title={title} className={`mt-1.5 break-words text-sm font-semibold text-slate-200 ${mono ? 'font-mono' : ''}`}>{displayed}</dd>
    </div>
  );
}

const stateIcon = (
  <svg aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M12 3l7 3v5c0 4.5-2.8 8.2-7 10-4.2-1.8-7-5.5-7-10V6l7-3z" />
  </svg>
);

export default function HardwareControlPage({
  guvenlikOlaylari = [],
  guvenlikOlaylariYukleniyor,
  guvenlikOlaylariHatasi,
  sonDegerlendirmeOlayi,
  sonAktiviteZamani,
}) {
  let stateContent = null;
  if (guvenlikOlaylariYukleniyor) {
    stateContent = <EmptyState icon={stateIcon} title="Değerlendirme yükleniyor" description="En son ESP32 güvenlik değerlendirmesi alınıyor." />;
  } else if (guvenlikOlaylariHatasi) {
    stateContent = <ErrorState icon={stateIcon} title="Değerlendirme alınamadı" description={guvenlikOlaylariHatasi} />;
  } else if (!guvenlikOlaylari.length) {
    stateContent = <EmptyState icon={stateIcon} title="Henüz güvenlik olayı yok" description="İlk güvenlik olayı alındığında ESP32 değerlendirmesi burada gösterilecek." />;
  } else if (!sonDegerlendirmeOlayi) {
    stateContent = <EmptyState icon={stateIcon} title="Değerlendirme bekleniyor" description="Güvenlik olayı alındı ancak henüz ESP32 assessment kaydı bulunmuyor." />;
  }

  if (stateContent) {
    return (
      <div className="flex w-full flex-col gap-6 pb-4 animate-fade-in">
        <PageHeader eyebrow="RİSK DEĞERLENDİRME" title="ESP32 Değerlendirmesi" description="En son güvenlik olayı ve ESP32 tarafından üretilen değerlendirme sonucu." />
        {stateContent}
      </div>
    );
  }

  const event = sonDegerlendirmeOlayi;
  const assessment = event.assessment;
  const decision = decisionAppearance(assessment.decision);
  const relatedFields = [
    ['Event ID', event.event_id, true],
    ['Kaynak IP', event.source_ip, true],
    ['Hedef port', event.destination_port],
    ['Protokol', event.protocol],
    ['Olay tipi', event.event_type],
    ['Komut', event.command || 'Veri yok', true],
    ['Taktik', event.tactic || 'Veri yok'],
    ['İşlenme durumu', assessment.processed ? 'İşlendi' : 'İşlenmedi'],
  ];

  return (
    <div className="flex w-full flex-col gap-6 pb-4 animate-fade-in">
      <PageHeader
        eyebrow="RİSK DEĞERLENDİRME"
        title="ESP32 Değerlendirmesi"
        description="En son güvenlik olayı ve ESP32 tarafından üretilen değerlendirme sonucu."
        meta={(
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
            <p className="text-xs font-medium text-slate-400">Son değerlendirme</p>
            <p className="mt-1 whitespace-nowrap text-sm font-semibold text-slate-200">{tarihSaatFormatla(sonAktiviteZamani)}</p>
          </div>
        )}
      />

      <section className="grid gap-4 rounded-3xl border border-indigo-500/20 bg-gradient-to-br from-slate-900 to-indigo-950/20 p-5 shadow-xl shadow-black/10 sm:p-6 md:grid-cols-2 xl:grid-cols-4">
        <div className="flex min-h-44 flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/55 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-400">ESP32 Kararı</p>
          <div className="mt-4">
            <StatusBadge status={decision.status} label={assessment.decision || 'Veri yok'} />
            <p className="mt-3 text-sm font-medium text-slate-300">{decision.explanation}</p>
          </div>
        </div>
        <div className="flex min-h-44 items-center justify-center rounded-2xl border border-slate-800 bg-slate-950/55 p-4">
          <div>
            <p className="mb-3 text-center text-xs font-semibold uppercase tracking-[0.15em] text-slate-400">ESP32 Risk Skoru</p>
            <RiskGauge value={assessment.risk_score} />
          </div>
        </div>
        <div className="flex min-h-44 flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/55 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-400">İşlenme Durumu</p>
          <StatusBadge status={assessment.processed ? 'success' : 'waiting'} label={assessment.processed ? 'İşlendi' : 'İşlenmedi'} />
        </div>
        <div className="flex min-h-44 min-w-0 flex-col justify-between rounded-2xl border border-slate-800 bg-slate-950/55 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-400">Device ID</p>
          <p title={assessment.device_id || 'Veri yok'} className="mt-4 break-all font-mono text-sm font-semibold text-indigo-200">{assessment.device_id || 'Veri yok'}</p>
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <RiskComparison inputRisk={event.input_risk_score} esp32Risk={assessment.risk_score} />
        <AssessmentTimeline event={event} assessment={assessment} />
      </div>

      <section className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950/70 p-5 shadow-lg shadow-black/10 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-400">Son assessment kaydı</p>
        <h2 className="mt-1 text-lg font-bold text-white">İlişkili Güvenlik Olayı</h2>
        <dl className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {relatedFields.map(([label, value, mono]) => (
            <Detail key={label} label={label} value={value} mono={mono} title={mono ? String(value) : undefined} />
          ))}
        </dl>
      </section>
    </div>
  );
}
