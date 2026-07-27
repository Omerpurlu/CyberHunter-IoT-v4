import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import { istatistikKartlariniOlustur } from '../utils/securitySummary';

export default function SystemInfoPage({ sistemLoglari, sunucuDurumu, esp32Durumu, aktifLed }) {
  const kartlar = istatistikKartlariniOlustur(sistemLoglari, esp32Durumu, aktifLed);
  const yetenekler = ['Hibrit Honeypot', 'Siber İstihbarat', 'Otomatik Karar', 'Kesintisiz Çalışma'];

  return (
    <div className="w-full flex flex-col gap-6 pb-8 animate-fade-in">
      <section className="relative shrink-0 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 p-7 md:p-8 shadow-lg">
        <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-indigo-500/10 blur-3xl"></div>
        <div className="relative z-10 grid gap-8 xl:grid-cols-[1.45fr_0.55fr] xl:items-center">
          <div>
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-extrabold tracking-tight text-white md:text-4xl">
                Cyber <span className="text-indigo-500">Hunter</span>
              </h1>
              <span className="rounded-full border border-indigo-500/25 bg-indigo-500/10 px-3 py-1 text-xs font-bold text-indigo-300">
                v1.0
              </span>
            </div>
            <h2 className="max-w-3xl text-xl font-semibold leading-relaxed text-slate-200">
              Yapay zekâ destekli, siber istihbarat toplayan fiziksel honeypot ve aktif savunma sistemi
            </h2>
            <p className="mt-5 max-w-3xl text-sm leading-7 text-slate-400">
              Gerçek bir sunucu gibi davranarak saldırganları kontrollü bir tuzak ortama çeker, saldırı davranışlarını analiz eder, tehdit seviyesini sınıflandırır ve gerektiğinde fiziksel donanım katmanında otomatik karşılık üretir.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              {['Fiziksel Honeypot', 'Yapay Zekâ Analizi', 'Siber İstihbarat', 'Aktif Savunma'].map((etiket, index) => (
                <span
                  key={etiket}
                  className={`rounded-xl border px-4 py-2 text-xs font-semibold ${[
                    'border-indigo-500/25 bg-indigo-500/10 text-indigo-300',
                    'border-cyan-500/25 bg-cyan-500/10 text-cyan-300',
                    'border-emerald-500/25 bg-emerald-500/10 text-emerald-300',
                    'border-amber-500/25 bg-amber-500/10 text-amber-300',
                  ][index]}`}
                >
                  {etiket}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Sistem durumu</p>
            <h3 className="mt-2 text-xl font-bold text-white">Koruma Katmanı Aktif</h3>
            <div className="mt-5 space-y-3">
              <div className="flex justify-between rounded-xl bg-slate-900 p-3 text-sm">
                <span className="text-slate-500">Bağlantı</span>
                <StatusBadge sunucuDurumu={sunucuDurumu} />
              </div>
              <div className="flex justify-between rounded-xl bg-slate-900 p-3 text-sm">
                <span className="text-slate-500">Cihaz</span>
                <span className="font-mono text-indigo-300">esp32-led-01</span>
              </div>
              <div className="flex justify-between rounded-xl bg-slate-900 p-3 text-sm">
                <span className="text-slate-500">Çalışma Modu</span>
                <span className="font-semibold text-slate-200">Hibrit Savunma</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-400">Canlı güvenlik özeti</p>
            <h3 className="mt-1 text-xl font-bold text-white">Operasyonel sistem görünümü</h3>
            <p className="mt-2 text-sm text-slate-500">Değerler mevcut loglar ve cihaz bağlantısından otomatik hesaplanır.</p>
          </div>
          <StatusBadge sunucuDurumu={sunucuDurumu} />
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {kartlar.map(kart => <StatCard key={kart.baslik} kart={kart} />)}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-lg">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-400">Sistem mimarisi</p>
        <h3 className="mt-1 text-xl font-bold text-white">CyberHunter Çalışma Prensibi</h3>
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {['Trafik Yakalama', 'Tuzak Ortam', 'AI Analizi', 'Fiziksel Müdahale'].map(ad => (
            <div key={ad} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
              <h4 className="font-bold text-white">{ad}</h4>
              <p className="mt-2 text-sm leading-6 text-slate-500">Saldırı davranışlarını görünür ve ölçülebilir hâle getirir.</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-xl font-bold text-white">Sistemin öne çıkan savunma katmanları</h3>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {yetenekler.map(ad => (
            <div key={ad} className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
              <h4 className="font-bold text-white">{ad}</h4>
              <p className="mt-2 text-sm leading-6 text-slate-500">Sistem güvenliği için bütünleşik savunma yaklaşımı sunar.</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
