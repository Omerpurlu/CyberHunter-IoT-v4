import { useEffect, useState } from 'react';
import api from '../services/api';

export default function useCyberHunterData() {
  const [guvenlikOlaylari, setGuvenlikOlaylari] = useState([]);
  const [guvenlikOlaylariYukleniyor, setGuvenlikOlaylariYukleniyor] = useState(true);
  const [guvenlikOlaylariHatasi, setGuvenlikOlaylariHatasi] = useState(null);
  const [sunucuDurumu, setSunucuDurumu] = useState('BAĞLANILIYOR...');
  const [sonYenilemeZamani, setSonYenilemeZamani] = useState(null);
  const [sistemSagligi, setSistemSagligi] = useState({
    raspberryPi: { durum: 'heartbeat_bekleniyor', sonBaglanti: null, sonVeri: null, hata: null },
    esp32: { durum: 'aktivite_yok', sonBaglanti: null, sonVeri: null, hata: null },
    fastapi: { durum: 'bekliyor', sonBaglanti: null, sonVeri: null, hata: null },
    postgresql: { durum: 'bekliyor', sonBaglanti: null, sonVeri: null, hata: null },
    dashboard: { durum: 'cevrimici', sonBaglanti: null, sonVeri: null, hata: null },
  });

  const verileriGetir = async () => {
    let baglantiVar = false;
    let veritabaniBaglantisiVar = false;
    let sonApiHatasi = null;
    let sonVeritabaniHatasi = null;
    let guvenlikOlaylariCevabi = null;
    let guvenlikHatasi = null;
    const hataMesaji = hata => hata?.response?.data?.detail || hata?.message || 'Bilinmeyen bağlantı hatası';

    try {
      const cevap = await api.get('/api/security-events', {
        params: { limit: 50, offset: 0 },
      });
      guvenlikOlaylariCevabi = Array.isArray(cevap.data?.items) ? cevap.data.items : [];
      setGuvenlikOlaylari(
        guvenlikOlaylariCevabi
      );
      setGuvenlikOlaylariHatasi(null);
      baglantiVar = true;
      veritabaniBaglantisiVar = true;
      setSonYenilemeZamani(Date.now());
    } catch (hata) {
      const mesaj = hataMesaji(hata);
      guvenlikHatasi = mesaj;
      setGuvenlikOlaylariHatasi(mesaj);
      sonApiHatasi = mesaj;
      sonVeritabaniHatasi = mesaj;
    } finally {
      setGuvenlikOlaylariYukleniyor(false);
    }

    const simdi = Date.now();
    const etkinGuvenlikOlaylari = guvenlikOlaylariCevabi ?? guvenlikOlaylari;
    const sonDegerlendirmeOlayi = etkinGuvenlikOlaylari.find(
      olay => olay && olay.assessment != null
    ) ?? null;
    const sonAktiviteOlayi = sonDegerlendirmeOlayi ?? etkinGuvenlikOlaylari[0] ?? null;
    const sonAktivite = sonAktiviteOlayi
      ? (
          sonAktiviteOlayi.assessment?.received_at
          ?? sonAktiviteOlayi.assessment?.assessed_at
          ?? sonAktiviteOlayi.received_at
          ?? sonAktiviteOlayi.event_timestamp
        )
      : null;
    setSistemSagligi(eski => ({
      raspberryPi: {
        durum: 'heartbeat_bekleniyor',
        sonBaglanti: null,
        sonVeri: etkinGuvenlikOlaylari[0]?.received_at ?? eski.raspberryPi.sonVeri,
        hata: guvenlikHatasi,
      },
      esp32: {
        durum: sonAktivite ? 'aktivite_alindi' : 'aktivite_yok',
        sonBaglanti: null,
        sonVeri: sonAktivite ?? eski.esp32.sonVeri,
        hata: guvenlikHatasi,
      },
      fastapi: {
        durum: baglantiVar ? 'cevrimici' : 'cevrimdisi',
        sonBaglanti: baglantiVar ? simdi : eski.fastapi.sonBaglanti,
        sonVeri: baglantiVar ? simdi : eski.fastapi.sonVeri,
        hata: baglantiVar ? null : sonApiHatasi,
      },
      postgresql: {
        durum: veritabaniBaglantisiVar ? 'cevrimici' : 'cevrimdisi',
        sonBaglanti: veritabaniBaglantisiVar ? simdi : eski.postgresql.sonBaglanti,
        sonVeri: veritabaniBaglantisiVar ? simdi : eski.postgresql.sonVeri,
        hata: veritabaniBaglantisiVar ? null : sonVeritabaniHatasi,
      },
      dashboard: {
        durum: 'cevrimici',
        sonBaglanti: simdi,
        sonVeri: baglantiVar ? simdi : eski.dashboard.sonVeri,
        hata: null,
      },
    }));
    setSunucuDurumu(baglantiVar ? 'ÇEVRİMİÇİ' : 'ÇEVRİMDIŞI');
  };

  useEffect(() => { verileriGetir(); const interval = setInterval(verileriGetir, 3000); return () => clearInterval(interval); }, []);
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
  return {
    guvenlikOlaylari,
    guvenlikOlaylariYukleniyor,
    guvenlikOlaylariHatasi,
    sonDegerlendirmeOlayi,
    sonAktiviteZamani,
    sunucuDurumu,
    sistemSagligi,
    sonYenilemeZamani,
  };
}
