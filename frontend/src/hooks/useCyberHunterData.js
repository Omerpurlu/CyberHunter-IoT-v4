import { useCallback, useEffect, useRef, useState } from 'react';
import { getHealth, getSecurityEvents, getSystemStatus } from '../services/api';

const guvenliHataMesaji = (hata, varsayilan) => {
  const durum = hata?.response?.status;
  return durum ? `${varsayilan} (HTTP ${durum})` : varsayilan;
};

export default function useCyberHunterData() {
  const [guvenlikOlaylari, setGuvenlikOlaylari] = useState([]);
  const [guvenlikOlaylariYukleniyor, setGuvenlikOlaylariYukleniyor] = useState(true);
  const [guvenlikOlaylariHatasi, setGuvenlikOlaylariHatasi] = useState(null);
  const [health, setHealth] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [systemStatusLoading, setSystemStatusLoading] = useState(true);
  const [healthError, setHealthError] = useState(null);
  const [systemStatusError, setSystemStatusError] = useState(null);
  const [sonYenilemeZamani, setSonYenilemeZamani] = useState(null);
  const mountedRef = useRef(false);
  const pollingRef = useRef(false);

  const verileriGetir = useCallback(async () => {
    if (pollingRef.current) return;
    pollingRef.current = true;

    try {
      const [eventsResult, healthResult, statusResult] = await Promise.allSettled([
        getSecurityEvents(),
        getHealth(),
        getSystemStatus(),
      ]);
      if (!mountedRef.current) return;

      if (eventsResult.status === 'fulfilled') {
        setGuvenlikOlaylari(
          Array.isArray(eventsResult.value.data?.items) ? eventsResult.value.data.items : []
        );
        setGuvenlikOlaylariHatasi(null);
      } else {
        setGuvenlikOlaylariHatasi(
          guvenliHataMesaji(eventsResult.reason, 'Güvenlik olayları alınamadı')
        );
      }

      if (healthResult.status === 'fulfilled') {
        setHealth(healthResult.value.data);
        setHealthError(null);
      } else {
        setHealthError(guvenliHataMesaji(healthResult.reason, 'Durum alınamadı'));
      }

      if (statusResult.status === 'fulfilled') {
        setSystemStatus(statusResult.value.data);
        setSystemStatusError(null);
      } else {
        setSystemStatusError(
          guvenliHataMesaji(statusResult.reason, 'Sistem durumu alınamadı')
        );
      }

      if ([eventsResult, healthResult, statusResult].some(result => result.status === 'fulfilled')) {
        setSonYenilemeZamani(Date.now());
      }
    } finally {
      if (mountedRef.current) {
        setGuvenlikOlaylariYukleniyor(false);
        setHealthLoading(false);
        setSystemStatusLoading(false);
      }
      pollingRef.current = false;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    verileriGetir();
    const interval = window.setInterval(verileriGetir, 3000);
    return () => {
      mountedRef.current = false;
      window.clearInterval(interval);
    };
  }, [verileriGetir]);

  const sonDegerlendirmeOlayi = guvenlikOlaylari.find(
    olay => olay && olay.assessment != null
  ) ?? null;
  const sonAktiviteZamani = sonDegerlendirmeOlayi
    ? (
        sonDegerlendirmeOlayi.assessment.received_at
        ?? sonDegerlendirmeOlayi.assessment.assessed_at
        ?? sonDegerlendirmeOlayi.received_at
        ?? sonDegerlendirmeOlayi.event_timestamp
      )
    : null;
  const fastapiHealthy = health?.fastapi?.status === 'healthy';

  return {
    guvenlikOlaylari,
    guvenlikOlaylariYukleniyor,
    guvenlikOlaylariHatasi,
    sonDegerlendirmeOlayi,
    sonAktiviteZamani,
    health,
    systemStatus,
    healthLoading,
    systemStatusLoading,
    healthError,
    systemStatusError,
    sonYenilemeZamani,
    sunucuDurumu: healthLoading
      ? 'BAĞLANILIYOR...'
      : fastapiHealthy
        ? 'ÇEVRİMİÇİ'
        : 'ÇEVRİMDIŞI',
  };
}
