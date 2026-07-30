export const statusConfig = {
  online: {
    label: 'Çevrimiçi',
    dot: 'bg-emerald-400',
    badge: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300',
  },
  success: {
    label: 'Başarılı',
    dot: 'bg-emerald-400',
    badge: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300',
  },
  waiting: {
    label: 'Bekleniyor',
    dot: 'bg-amber-400',
    badge: 'border-amber-500/25 bg-amber-500/10 text-amber-300',
  },
  warning: {
    label: 'Uyarı',
    dot: 'bg-amber-400',
    badge: 'border-amber-500/25 bg-amber-500/10 text-amber-300',
  },
  offline: {
    label: 'Çevrimdışı',
    dot: 'bg-red-400',
    badge: 'border-red-500/25 bg-red-500/10 text-red-300',
  },
  error: {
    label: 'Hata',
    dot: 'bg-red-400',
    badge: 'border-red-500/25 bg-red-500/10 text-red-300',
  },
  activity: {
    label: 'Aktivite alındı',
    dot: 'bg-indigo-400',
    badge: 'border-indigo-500/25 bg-indigo-500/10 text-indigo-300',
  },
  interface: {
    label: 'Arayüz çalışıyor',
    dot: 'bg-purple-400',
    badge: 'border-purple-500/25 bg-purple-500/10 text-purple-300',
  },
  unknown: {
    label: 'Bilinmiyor',
    dot: 'bg-slate-500',
    badge: 'border-slate-700 bg-slate-800/70 text-slate-300',
  },
};

export function getStatusConfig(status = 'unknown') {
  return statusConfig[status] || statusConfig.unknown;
}
