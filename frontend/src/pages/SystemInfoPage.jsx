import ArchitectureFlow from '../components/ArchitectureFlow';
import InfoFeatureCard from '../components/InfoFeatureCard';
import PageHeader from '../components/PageHeader';
import SystemLiveSummary from '../components/SystemLiveSummary';
import { tarihSaatFormatla } from '../utils/dateFormat';
import { componentByType, computedStatusLabel } from '../utils/systemStatus';

function Icon({ path }) {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d={path} />
    </svg>
  );
}

const benefits = ['Hızlı tespit', 'Otomatik değerlendirme', 'Güvenilir kayıt'];
const components = [
  ['Raspberry Pi', 'Bridge ve SDA/SCL veri aktarımı'],
  ['ESP32', 'Risk değerlendirmesi'],
  ['FastAPI', 'API ve iş mantığı'],
  ['PostgreSQL', 'Kalıcı veri saklama'],
  ['Dashboard', 'İzleme ve inceleme'],
];
const integrityItems = [
  'Her güvenlik olayı benzersiz olarak kaydedilir',
  'Aynı veri tekrar gelirse ikinci kez oluşturulmaz',
  'Tutarsız veya hatalı kayıtlar sisteme alınmaz',
  'Olay ve ESP32 değerlendirmesi birlikte saklanır',
  'Kayıtlar PostgreSQL üzerinde güvenli biçimde korunur',
];

export default function SystemInfoPage({
  guvenlikOlaylari,
  guvenlikOlaylariYukleniyor,
  guvenlikOlaylariHatasi,
  sonDegerlendirmeOlayi,
  sonAktiviteZamani,
  health,
  systemStatus,
  healthError,
  systemStatusError,
}) {
  const raspberryPi = componentByType(systemStatus, 'raspberry_pi');
  const esp32 = componentByType(systemStatus, 'esp32');
  const liveItems = [
    ['FastAPI', health?.fastapi?.status === 'healthy' ? 'Sağlıklı' : health ? 'Kısıtlı' : 'Durum alınamadı'],
    ['PostgreSQL', health?.postgresql?.status === 'healthy' ? 'Sağlıklı' : health?.postgresql?.status === 'unavailable' ? 'Kullanılamıyor' : 'Durum alınamadı'],
    ['Sorgu süresi', Number.isFinite(health?.postgresql?.query_ms) ? `${health.postgresql.query_ms} ms` : 'Veri yok'],
    ['Raspberry Pi', computedStatusLabel(raspberryPi?.computed_status || 'waiting')],
    ['ESP32', computedStatusLabel(esp32?.computed_status || 'waiting')],
  ];
  return (
    <div className="flex w-full flex-col gap-6 pb-4 animate-fade-in lg:gap-7">
      <PageHeader
        eyebrow="SİSTEM GENEL BAKIŞ"
        title="Sistem Bilgisi"
        description="CyberHunter projesinin amacı, bileşenleri ve uçtan uca güvenlik mimarisi hakkında genel bilgiler."
        meta={(
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
            <p className="text-xs font-medium text-slate-400">Son güncelleme</p>
            <p className="mt-1 whitespace-nowrap text-sm font-semibold text-slate-200">
              {tarihSaatFormatla(sonAktiviteZamani)}
            </p>
          </div>
        )}
      />

      <section aria-label="Canlı sistem özeti" className="rounded-3xl border border-slate-800 bg-slate-900/65 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-300">Canlı bağlantı özeti</p>
            <h2 className="mt-1 text-lg font-bold text-white">Health ve heartbeat durumu</h2>
          </div>
          <p className="text-xs text-slate-400">Son health kontrolü: {tarihSaatFormatla(health?.generated_at)}</p>
        </div>
        <dl className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {liveItems.map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3">
              <dt className="text-xs font-medium text-slate-400">{label}</dt>
              <dd className="mt-1 text-sm font-semibold text-slate-200">{value}</dd>
            </div>
          ))}
        </dl>
        {(healthError || systemStatusError) && (
          <p className="mt-4 text-xs text-amber-300">Bazı canlı durum bilgileri geçici olarak alınamadı; son başarılı değerler korunuyor.</p>
        )}
      </section>

      <section className="relative overflow-hidden rounded-3xl border border-indigo-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/25 p-5 shadow-xl shadow-black/10 sm:p-6 lg:p-7">
        <div aria-hidden="true" className="pointer-events-none absolute -left-20 -top-24 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="relative grid gap-7 xl:grid-cols-[0.58fr_1.42fr] xl:items-center">
          <div>
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-indigo-400/20 bg-indigo-500/10 text-indigo-300 shadow-lg shadow-indigo-950/30">
              <svg aria-hidden="true" className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" d="M12 3l7 3v5c0 4.5-2.8 8.2-7 10-4.2-1.8-7-5.5-7-10V6l7-3zm-3 9l2 2 4-5" />
              </svg>
            </div>
            <p className="mt-5 text-xs font-semibold uppercase tracking-[0.18em] text-indigo-300">
              CyberHunter güvenlik platformu
            </p>
            <h2 className="mt-2 max-w-xl text-2xl font-bold leading-tight text-white sm:text-3xl">
              IoT güvenlik olaylarını uçtan uca izleme ve değerlendirme sistemi
            </h2>
            <ul className="mt-5 space-y-3">
              {[
                'Saldırı verisi izlenir',
                'ESP32 tarafından değerlendirilir',
                "PostgreSQL'de bütünlüklü biçimde saklanır",
              ].map(item => (
                <li key={item} className="flex items-center gap-3 text-sm text-slate-300">
                  <span aria-hidden="true" className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-300">✓</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="min-w-0 rounded-3xl border border-slate-800 bg-slate-950/55 p-4 sm:p-5">
            <div className="mb-5">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Uçtan uca mimari</p>
              <h3 className="mt-1 text-lg font-bold text-white">Güvenlik verisinin izlediği yol</h3>
            </div>
            <ArchitectureFlow />
          </div>
        </div>
      </section>

      <section aria-label="CyberHunter proje bilgileri" className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4 xl:gap-5">
        <InfoFeatureCard
          title="Proje Amacı"
          accent="indigo"
          icon={<Icon path="M12 3l7 3v5c0 4.5-2.8 8.2-7 10-4.2-1.8-7-5.5-7-10V6l7-3z" />}
        >
          <p>
            IoT cihazlarından gelen güvenlik olaylarını toplamak, ESP32 üzerinde değerlendirmek ve
            doğrulanmış sonucu güvenli biçimde kalıcı veritabanına kaydetmek.
          </p>
          <ul className="mt-4 flex flex-wrap gap-2">
            {benefits.map(benefit => (
              <li key={benefit} className="rounded-lg border border-indigo-500/15 bg-indigo-500/5 px-2.5 py-1 text-xs font-medium text-indigo-200">
                {benefit}
              </li>
            ))}
          </ul>
        </InfoFeatureCard>

        <InfoFeatureCard
          title="Bileşenler"
          accent="rose"
          icon={<Icon path="M7 7h10v10H7zM9 3v4m6-4v4M9 17v4m6-4v4M3 9h4m10 0h4M3 15h4m10 0h4" />}
        >
          <ul className="space-y-2.5">
            {components.map(([name, role]) => (
              <li key={name} className="flex gap-2">
                <span className="font-semibold text-slate-200">{name}</span>
                <span aria-hidden="true" className="text-slate-600">—</span>
                <span>{role}</span>
              </li>
            ))}
          </ul>
        </InfoFeatureCard>

        <InfoFeatureCard
          title="Veriler Nasıl Korunuyor?"
          accent="emerald"
          icon={<Icon path="M5 12l4 4L19 6M4 4h16v16H4z" />}
        >
          <ul className="space-y-2.5">
            {integrityItems.map(item => (
              <li key={item} className="flex gap-2">
                <span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-slate-500">
            Tekrarlanan veya çelişkili veriler otomatik olarak kontrol edilir.
          </p>
        </InfoFeatureCard>

        <SystemLiveSummary
          guvenlikOlaylari={guvenlikOlaylari}
          sonDegerlendirmeOlayi={sonDegerlendirmeOlayi}
          guvenlikOlaylariYukleniyor={guvenlikOlaylariYukleniyor}
          guvenlikOlaylariHatasi={guvenlikOlaylariHatasi}
        />
      </section>

      <footer className="rounded-2xl border border-slate-800 bg-slate-900/60 px-5 py-4 text-center text-sm text-slate-400">
        Bu sayfa CyberHunter projesinin tanıtımı ve uçtan uca mimari özeti için hazırlanmıştır.
      </footer>
    </div>
  );
}
