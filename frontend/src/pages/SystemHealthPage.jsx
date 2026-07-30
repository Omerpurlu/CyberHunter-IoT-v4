import HealthCard from '../components/HealthCard';
import HealthOverview from '../components/HealthOverview';
import PageHeader from '../components/PageHeader';
import { tarihSaatFormatla } from '../utils/dateFormat';

function ComponentIcon({ path }) {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d={path} />
    </svg>
  );
}

export default function SystemHealthPage({ sistemSagligi = {}, sonYenilemeZamani }) {
  const raspberryPi = sistemSagligi.raspberryPi || {};
  const esp32 = sistemSagligi.esp32 || {};
  const fastapi = sistemSagligi.fastapi || {};
  const postgresql = sistemSagligi.postgresql || {};
  const apiErisilebilir = fastapi.durum === 'cevrimici';
  const veritabaniErisilebilir = postgresql.durum === 'cevrimici';
  const esp32AktivitesiVar = esp32.durum === 'aktivite_alindi';

  return (
    <div className="flex w-full flex-col gap-5 pb-4 animate-fade-in sm:gap-6">
      <PageHeader
        eyebrow="UÇTAN UCA İZLEME"
        title="Sistem Sağlığı"
        description="Bileşen durumları, API aktiviteleri ve gelecekteki heartbeat sinyalleri üzerinden izlenir."
        meta={(
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
            <p className="text-xs font-medium text-slate-400">Son yenileme</p>
            <p className="mt-1 whitespace-nowrap text-sm font-semibold text-slate-200">
              {tarihSaatFormatla(sonYenilemeZamani)}
            </p>
          </div>
        )}
      />

      <HealthOverview apiAccessible={apiErisilebilir} databaseAccessible={veritabaniErisilebilir} />

      <section aria-label="Sistem bileşenleri" className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
        <HealthCard
          name="Raspberry Pi"
          role="Bridge ve veri toplama katmanı"
          status="waiting"
          statusLabel="Heartbeat bekleniyor"
          timeLabel="Son olay aktivitesi"
          time={raspberryPi.sonVeri}
          emptyTimeText="Henüz aktivite alınmadı"
          source="Security event aktivitesi"
          description="Gerçek bağlantı durumu heartbeat entegrasyonundan sonra gösterilecek."
          icon={<ComponentIcon path="M7 7h10v10H7zM9 3v4m6-4v4M9 17v4m6-4v4" />}
          iconTone="amber"
          className="xl:col-span-2"
        />
        <HealthCard
          name="ESP32"
          role="Güvenlik değerlendirme katmanı"
          status={esp32AktivitesiVar ? 'activity' : 'unknown'}
          statusLabel={esp32AktivitesiVar ? 'Son aktivite alındı' : 'Henüz değerlendirme alınmadı'}
          timeLabel="Son değerlendirme aktivitesi"
          time={esp32.sonVeri}
          emptyTimeText="Henüz değerlendirme alınmadı"
          source="Güvenlik değerlendirmesi"
          description={esp32AktivitesiVar ? 'Son ESP32 değerlendirme verisi başarıyla alındı.' : 'Henüz ESP32 değerlendirme verisi alınmadı.'}
          icon={<ComponentIcon path="M7 7h10v10H7zM3 9h4m10 0h4M3 15h4m10 0h4" />}
          iconTone="blue"
          className="xl:col-span-2"
        />
        <HealthCard
          name="FastAPI"
          role="API ve iş mantığı katmanı"
          status={apiErisilebilir ? 'success' : 'error'}
          statusLabel={apiErisilebilir ? 'Erişilebilir' : 'Erişilemiyor'}
          timeLabel="Son başarılı API yenilemesi"
          time={sonYenilemeZamani}
          source="Security-events API isteği"
          description={apiErisilebilir ? 'API servisi isteğe yanıt veriyor.' : 'API servisine erişilemiyor; son başarılı yenileme korunuyor.'}
          error={fastapi.hata}
          pulse={apiErisilebilir}
          icon={<ComponentIcon path="M13 2L5 14h6l-1 8 9-13h-6z" />}
          iconTone="emerald"
          className="xl:col-span-2"
        />
        <HealthCard
          name="PostgreSQL"
          role="Kalıcı veri depolama katmanı"
          status={veritabaniErisilebilir ? 'success' : 'error'}
          statusLabel={veritabaniErisilebilir ? 'Sorgu başarılı' : 'Veritabanı erişim hatası'}
          timeLabel="Son başarılı security-events sorgusu"
          time={sonYenilemeZamani}
          source="API sorgusundan türetildi"
          description={veritabaniErisilebilir ? 'Güvenlik olayları PostgreSQL üzerinden okunabiliyor.' : 'Security-events sorgusu üzerinden veritabanı erişimi doğrulanamadı.'}
          error={postgresql.hata}
          pulse={veritabaniErisilebilir}
          icon={<ComponentIcon path="M5 6c0-2 3-3 7-3s7 1 7 3-3 3-7 3-7-1-7-3zm0 0v12c0 2 3 3 7 3s7-1 7-3V6" />}
          iconTone="teal"
          className="xl:col-span-2 xl:col-start-2"
        />
        <HealthCard
          name="Dashboard"
          role="İzleme ve inceleme arayüzü"
          status="interface"
          statusLabel="Arayüz çalışıyor"
          timeLabel="Son başarılı veri yenilemesi"
          time={sonYenilemeZamani}
          source="React arayüzü ve API yenilemesi"
          description={apiErisilebilir ? 'Kullanıcı arayüzü aktif ve veri yenileme çalışıyor.' : 'Kullanıcı arayüzü aktif; API veri bağlantısı şu anda kullanılamıyor.'}
          icon={<ComponentIcon path="M4 5h16v12H4zM9 21h6M12 17v4" />}
          iconTone="purple"
          className="xl:col-span-2 xl:col-start-4"
        />
      </section>

      <footer className="flex min-h-12 items-center rounded-2xl border border-amber-500/15 bg-amber-500/5 px-4 py-3 text-sm leading-5 text-amber-200/90 sm:px-5">
        <svg aria-hidden="true" className="mr-3 h-5 w-5 shrink-0 text-amber-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M12 9v4m0 4h.01M10 3h4l7 15H3l7-15z" />
        </svg>
        Heartbeat entegrasyonu tamamlandığında Raspberry Pi ve ESP32 bileşenlerinin gerçek bağlantı durumları otomatik güncellenecektir.
      </footer>
    </div>
  );
}
