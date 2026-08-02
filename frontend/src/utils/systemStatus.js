const computedLabels = {
  waiting: 'Heartbeat bekleniyor',
  online: 'Çevrimiçi',
  delayed: 'Gecikmeli',
  offline: 'Çevrimdışı',
};

const reportedLabels = {
  healthy: 'Sağlıklı',
  degraded: 'Kısıtlı',
  error: 'Hata',
  starting: 'Başlatılıyor',
};

export const computedStatusLabel = status => computedLabels[status] || 'Bilinmiyor';
export const reportedStatusLabel = status => reportedLabels[status] || (status ? 'Bilinmiyor' : 'Veri yok');
export const componentByType = (systemStatus, type) => (
  Array.isArray(systemStatus?.components)
    ? systemStatus.components.find(component => component?.component_type === type) || null
    : null
);

export const healthBadgeStatus = status => {
  if (status === 'healthy') return 'success';
  if (status === 'degraded') return 'warning';
  if (status === 'unavailable') return 'error';
  return 'unknown';
};
