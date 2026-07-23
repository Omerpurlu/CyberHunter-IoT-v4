import { useEffect, useState } from 'react';
import api from '../services/api';

export default function useCyberHunterData() {
  const [grafikVerileri, setGrafikVerileri] = useState([]);
  const [sistemLoglari, setSistemLoglari] = useState([]);
  const [sunucuDurumu, setSunucuDurumu] = useState('BAĞLANILIYOR...');
  const [esp32Durumu, setEsp32Durumu] = useState('BAĞLANILIYOR...');
  const [aktifLed, setAktifLed] = useState('off');
  const [komutDurumu, setKomutDurumu] = useState('');

  const verileriGetir = async () => {
    let baglantiVar = false;
    try { const cevap = await api.get('/api/stats'); setGrafikVerileri(Array.isArray(cevap.data) ? cevap.data : []); baglantiVar = true; }
    catch { setGrafikVerileri([]); }
    try { const cevap = await api.get('/api/logs'); setSistemLoglari(Array.isArray(cevap.data) ? cevap.data : []); baglantiVar = true; }
    catch { setSistemLoglari([]); }
    try {
      const cevap = await api.get('/api/iot/devices/esp32-led-01/state');
      setAktifLed(cevap.data.led || 'off');
      setEsp32Durumu(cevap.data.online ? 'ÇEVRİMİÇİ' : 'ÇEVRİMDIŞI');
      baglantiVar = true;
    } catch { setAktifLed('off'); setEsp32Durumu('ÇEVRİMDIŞI'); }
    setSunucuDurumu(baglantiVar ? 'ÇEVRİMİÇİ' : 'ÇEVRİMDIŞI');
  };

  const komutGonder = async (komutTuru) => {
    try {
      setKomutDurumu('Gönderiliyor...');
      await api.post('/api/iot/commands', { device_id: 'esp32-led-01', komut: komutTuru });
      setKomutDurumu('Komut başarıyla iletildi!');
    } catch { setKomutDurumu('Hata: Komut iletilemedi!'); }
    setTimeout(() => setKomutDurumu(''), 3000);
  };

  useEffect(() => { verileriGetir(); const interval = setInterval(verileriGetir, 3000); return () => clearInterval(interval); }, []);
  return { grafikVerileri, sistemLoglari, sunucuDurumu, esp32Durumu, aktifLed, komutDurumu, verileriGetir, komutGonder };
}
