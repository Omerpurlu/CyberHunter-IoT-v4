import { getStatusConfig } from '../utils/statusConfig';

export default function StatusBadge({ status, label, pulse = false, sunucuDurumu }) {
  const legacyStatus = sunucuDurumu === 'ÇEVRİMİÇİ'
    ? 'online'
    : sunucuDurumu === 'BAĞLANILIYOR...'
      ? 'waiting'
      : 'offline';
  const resolvedStatus = status || legacyStatus;
  const config = getStatusConfig(resolvedStatus);
  const resolvedLabel = label || sunucuDurumu || config.label;

  return (
    <span className={`inline-flex min-h-7 shrink-0 items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${config.badge}`}>
      <span
        aria-hidden="true"
        className={`h-2 w-2 rounded-full ${config.dot} ${pulse ? 'status-pulse' : ''}`}
      />
      {resolvedLabel}
    </span>
  );
}
