import HealthCard from '../components/HealthCard';
import HealthOverview from '../components/HealthOverview';
import PageHeader from '../components/PageHeader';
import { tarihSaatFormatla } from '../utils/dateFormat';
import {
  componentByType,
  computedStatusLabel,
  healthBadgeStatus,
  reportedStatusLabel,
} from '../utils/systemStatus';

function ComponentIcon({ path }) {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d={path} />
    </svg>
  );
}

const ageLabel = value => Number.isFinite(value) ? `${value.toFixed(1)} sn` : 'Veri yok';

function componentDetails(component) {
  if (!component || component.computed_status === 'waiting') return [];
  return [
    ['Bileşen kimliği', component.component_id],
    ['Bildirilen durum', reportedStatusLabel(component.reported_status)],
    ['Sinyal yaşı', ageLabel(component.age_seconds)],
    ['Sequence', component.sequence],
    ['Yazılım sürümü', component.software_version],
  ];
}

export default function SystemHealthPage({
  health,
  systemStatus,
  healthLoading,
  systemStatusLoading,
  healthError,
  systemStatusError,
  sonYenilemeZamani,
}) {
  const raspberryPi = componentByType(systemStatus, 'raspberry_pi');
  const esp32 = componentByType(systemStatus, 'esp32');
  const fastapiStatus = health?.fastapi?.status;
  const postgresqlStatus = health?.postgresql?.status;
  const healthAvailable = Boolean(health);
  const statusAvailable = Boolean(systemStatus);

  const renderComponentCard = (name, role, component, icon, iconTone) => {
    const unavailable = !statusAvailable && !systemStatusLoading;
    const computedStatus = component?.computed_status || 'waiting';
    const waiting = computedStatus === 'waiting';
    return (
      <HealthCard
        name={name}
        role={role}
        status={unavailable ? 'unknown' : ['waiting', 'online', 'delayed', 'offline'].includes(computedStatus) ? computedStatus : 'unknown'}
        statusLabel={unavailable ? 'Sistem durumu alınamadı' : computedStatusLabel(computedStatus)}
        timeLabel="Son heartbeat"
        time={component?.last_seen}
        emptyTimeText={waiting ? 'Heartbeat bekleniyor' : 'Veri yok'}
        source="Heartbeat"
        description={unavailable ? 'Sistem durumu alınamadı.' : waiting ? 'Heartbeat bekleniyor' : `${name} bağlantı durumu gerçek heartbeat verisinden hesaplandı.`}
        error={!statusAvailable && !systemStatusLoading ? systemStatusError : null}
        pulse={computedStatus === 'online'}
        icon={icon}
        iconTone={iconTone}
        details={componentDetails(component)}
        className="xl:col-span-3"
      />
    );
  };

  return (
    <div className="flex w-full flex-col gap-5 pb-4 animate-fade-in sm:gap-6">
      <PageHeader
        eyebrow="UÇTAN UCA İZLEME"
        title="Sistem Sağlığı"
        description="FastAPI, PostgreSQL ve cihaz bağlantıları gerçek health ve heartbeat verileriyle izlenir."
        meta={(
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
            <p className="text-xs font-medium text-slate-400">Son yenileme</p>
            <p className="mt-1 whitespace-nowrap text-sm font-semibold text-slate-200">
              {tarihSaatFormatla(sonYenilemeZamani)}
            </p>
          </div>
        )}
      />

      <HealthOverview
        apiAccessible={fastapiStatus === 'healthy'}
        databaseAccessible={postgresqlStatus === 'healthy'}
        deviceStatuses={[raspberryPi?.computed_status, esp32?.computed_status]}
      />

      <section aria-label="Sistem bileşenleri" className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
        {renderComponentCard(
          'Raspberry Pi',
          'Bridge ve veri toplama katmanı',
          raspberryPi,
          <ComponentIcon path="M7 7h10v10H7zM9 3v4m6-4v4M9 17v4m6-4v4" />,
          'amber'
        )}
        {renderComponentCard(
          'ESP32',
          'Güvenlik değerlendirme katmanı',
          esp32,
          <ComponentIcon path="M7 7h10v10H7zM3 9h4m10 0h4M3 15h4m10 0h4" />,
          'blue'
        )}
        <HealthCard
          name="FastAPI"
          role="API ve iş mantığı katmanı"
          status={healthBadgeStatus(fastapiStatus)}
          statusLabel={healthLoading ? 'Durum alınıyor' : healthError ? 'Durum alınamadı' : fastapiStatus === 'healthy' ? 'Sağlıklı' : healthAvailable ? 'Kısıtlı' : 'Durum alınamadı'}
          timeLabel="Son health kontrolü"
          time={health?.generated_at}
          source="GET /api/health"
          description={healthAvailable ? 'FastAPI durumu doğrudan health endpointinden alındı.' : 'FastAPI durumu alınamadı.'}
          error={!healthLoading ? healthError : null}
          pulse={fastapiStatus === 'healthy'}
          icon={<ComponentIcon path="M13 2L5 14h6l-1 8 9-13h-6z" />}
          iconTone="emerald"
          className="xl:col-span-3"
        />
        <HealthCard
          name="PostgreSQL"
          role="Kalıcı veri depolama katmanı"
          status={healthBadgeStatus(postgresqlStatus)}
          statusLabel={healthLoading ? 'Durum alınıyor' : healthError ? 'Durum alınamadı' : postgresqlStatus === 'healthy' ? 'Sağlıklı' : postgresqlStatus === 'unavailable' ? 'Kullanılamıyor' : 'Durum alınamadı'}
          timeLabel="Son health kontrolü"
          time={health?.generated_at}
          source="GET /api/health"
          description={healthAvailable ? 'PostgreSQL bağlantısı SELECT 1 ile doğrulandı.' : 'PostgreSQL durumu alınamadı.'}
          error={!healthLoading ? healthError : null}
          icon={<ComponentIcon path="M5 6c0-2 3-3 7-3s7 1 7 3-3 3-7 3-7-1-7-3zm0 0v12c0 2 3 3 7 3s7-1 7-3V6" />}
          iconTone="teal"
          details={healthAvailable ? [['Sorgu süresi', Number.isFinite(health?.postgresql?.query_ms) ? `${health.postgresql.query_ms} ms` : 'Veri yok']] : []}
          className="xl:col-span-3"
        />
      </section>
    </div>
  );
}
