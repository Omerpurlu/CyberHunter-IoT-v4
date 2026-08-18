import StatusBadge from './StatusBadge';
import { tarihSaatFormatla } from '../utils/dateFormat';

const labels = {
  severity: { normal: 'Normal', warning: 'Uyarı', critical: 'Kritik' },
  action: {
    log_only: 'Yalnızca Kaydet',
    alert: 'Uyarı Oluşturuldu',
    request_approval: 'Yönetici Onayı Bekleniyor',
    isolate_device: 'Cihaz İzolasyonu İstendi',
  },
  status: {
    recorded: 'Kaydedildi', awaiting_approval: 'Onay Bekliyor', pending: 'ESP32 Komutu Bekliyor',
    dispatched: "ESP32'ye Gönderildi", executed: 'Uygulandı', failed: 'Başarısız',
    expired: 'Süresi Doldu', cancelled: 'İptal Edildi',
  },
  relay: {
    simulated_isolated: 'Simülasyon: İzolasyon Başarılı', isolated: 'Fiziksel İzolasyon Doğrulandı',
    not_changed: 'Değişiklik Yapılmadı', connected: 'Bağlı', unknown: 'Durum Bilinmiyor',
  },
};

const statusStyles = {
  recorded: 'unknown', awaiting_approval: 'warning', pending: 'waiting', dispatched: 'activity',
  executed: 'success', failed: 'error', expired: 'unknown', cancelled: 'unknown',
};

function valueLabel(group, value, fallback = 'Veri yok') {
  if (value === null || value === undefined || value === '') return fallback;
  return labels[group]?.[value] ?? String(value);
}

function Field({ label, value, mono = false }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3.5">
      <dt className="text-xs font-medium text-slate-400">{label}</dt>
      <dd className={`mt-1.5 break-words text-sm font-semibold text-slate-200 ${mono ? 'font-mono' : ''}`}>
        {value === null || value === undefined || value === '' ? 'Veri yok' : value}
      </dd>
    </div>
  );
}

export default function ResponseActionDetails({ action, count, loading, error }) {
  if (loading && !action) return <p className="text-sm text-slate-400">Müdahale kayıtları yükleniyor...</p>;
  if (error && !action) return <p role="alert" className="text-sm text-red-300">Müdahale kayıtları alınamadı.</p>;
  if (!action) return <p className="text-sm text-slate-400">Müdahale kaydı bulunmuyor.</p>;

  const lifecycle = [
    ['Karar oluşturuldu', action.created_at],
    ["ESP32'ye gönderildi", action.dispatched_at],
    ['Uygulama sonucu alındı', action.executed_at],
    ['ACK alındı', action.ack_received_at],
  ];

  return (
    <div className="space-y-5">
      {error && <p className="rounded-xl border border-amber-500/25 bg-amber-500/10 p-3 text-xs text-amber-300">Yeni müdahale kayıtları alınamadı; son başarılı veri gösteriliyor.</p>}
      {count > 1 && <p className="text-xs text-slate-400">Bu olay için {count} müdahale kaydı var. En güncel kayıt gösteriliyor.</p>}
      <div className="flex flex-wrap gap-2">
        <StatusBadge status={statusStyles[action.status] ?? 'unknown'} label={valueLabel('status', action.status, 'Durum bilinmiyor')} />
        <StatusBadge status={action.severity === 'critical' ? 'error' : action.severity === 'warning' ? 'warning' : 'unknown'} label={valueLabel('severity', action.severity)} />
      </div>
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-indigo-400">Müdahale Kararı</h3>
        <dl className="grid gap-3 sm:grid-cols-2">
          <Field label="Seviye" value={valueLabel('severity', action.severity)} />
          <Field label="Aksiyon" value={valueLabel('action', action.action)} />
          <Field label="Durum" value={valueLabel('status', action.status, 'Durum bilinmiyor')} />
          <Field label="Risk" value={action.risk_score == null ? null : `${action.risk_score} / 100`} />
          <Field label="Policy Version" value={action.policy_version} />
          <Field label="Karar Açıklaması" value={action.decision_reason} />
        </dl>
      </section>
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-indigo-400">ESP32 Komut Sonucu</h3>
        <dl className="grid gap-3 sm:grid-cols-2">
          <Field label="Device ID" value={action.device_id} mono />
          <Field label="Röle Durumu" value={valueLabel('relay', action.relay_state, 'Durum Bilinmiyor')} />
          <Field label="Deneme Sayısı" value={action.attempt_count} />
          <Field label="Gönderilme Zamanı" value={action.dispatched_at ? tarihSaatFormatla(action.dispatched_at) : null} />
          <Field label="Uygulanma Zamanı" value={action.executed_at ? tarihSaatFormatla(action.executed_at) : null} />
          <Field label="ACK Alınma Zamanı" value={action.ack_received_at ? tarihSaatFormatla(action.ack_received_at) : null} />
          <Field label="ACK Mesajı" value={action.ack_message} />
          <Field label="Son Hata" value={action.last_error} />
        </dl>
      </section>
      {action.relay_state === 'simulated_isolated' && (
        <p className="rounded-xl border border-indigo-500/25 bg-indigo-500/10 p-3 text-sm text-indigo-200">
          Bu sonuç yazılımsal dry-run testine aittir. Fiziksel röle henüz devreye alınmadı.
        </p>
      )}
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-indigo-400">Müdahale Yaşam Döngüsü</h3>
        <ol className="space-y-2">
          {lifecycle.map(([label, timestamp]) => (
            <li key={label} className="flex items-center gap-2 text-sm">
              <span className={timestamp ? 'text-emerald-400' : 'text-slate-600'}>{timestamp ? '✓' : '○'}</span>
              <span className={timestamp ? 'text-slate-200' : 'text-slate-500'}>{label}</span>
              {timestamp && <time className="ml-auto text-xs text-slate-500">{tarihSaatFormatla(timestamp)}</time>}
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
