import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function App() {
  // Sayfa geçişleri için state
  const [aktifSayfa, setAktifSayfa] = useState('kontrol'); // Varsayılan olarak yeni sayfayı açalım
  
  // Backend'den gelecek verileri tutacağımız state'ler
  const [grafikVerileri, setGrafikVerileri] = useState([]);
  const [sistemLoglari, setSistemLoglari] = useState([]);
  const [sunucuDurumu, setSunucuDurumu] = useState('BAĞLANILIYOR...');
  const [esp32Durumu, setEsp32Durumu] = useState('BAĞLANILIYOR...');
  
  // DONANIM KONTROLÜ İÇİN YENİ STATE'LER
  const [aktifLed, setAktifLed] = useState('off'); // 'red', 'blue', 'off'
  const [komutDurumu, setKomutDurumu] = useState('');

  // Python sunucusundan veri çeken ana fonksiyon
  const verileriGetir = async () => {
  const BASE_URL = 'http://10.104.1.89:5000';
  let baglantiVar = false;

  // 1. Grafik verileri
  try {
    const grafikCevap = await axios.get(`${BASE_URL}/api/stats`);

    setGrafikVerileri(
      Array.isArray(grafikCevap.data) ? grafikCevap.data : []
    );

    baglantiVar = true;
  } catch (error) {
    setGrafikVerileri([]);
  }

  // 2. Sistem logları
  try {
    const logCevap = await axios.get(`${BASE_URL}/api/logs`);

    setSistemLoglari(
      Array.isArray(logCevap.data) ? logCevap.data : []
    );

    baglantiVar = true;
  } catch (error) {
    setSistemLoglari([]);
  }

  // 3. ESP32 LED durumu
  try {
    const cihazCevap = await axios.get(
      `${BASE_URL}/api/iot/devices/esp32-led-01/state`
    );

    setAktifLed(cihazCevap.data.led || 'off');
    setEsp32Durumu('ÇEVRİMİÇİ');
    baglantiVar = true;
  } catch (error) {
    setAktifLed('off');
    setEsp32Durumu('ÇEVRİMDIŞI');
  }

  setSunucuDurumu(
    baglantiVar ? 'ÇEVRİMİÇİ' : 'ÇEVRİMDIŞI'
  );
};

  // ESP32'ye Komut Gönderme Fonksiyonu
  const komutGonder = async (komutTuru) => {
    try {
      setKomutDurumu('Gönderiliyor...');
      await axios.post('http://10.104.1.89:5000/api/iot/commands', {
        device_id: 'esp32-led-01',
        komut: komutTuru
      });
      setKomutDurumu('Komut başarıyla iletildi!');
      
      // Bildirimi 3 saniye sonra temizle
      setTimeout(() => setKomutDurumu(''), 3000);
    } catch (error) {
      setKomutDurumu('Hata: Komut iletilemedi!');
      setTimeout(() => setKomutDurumu(''), 3000);
    }
  };

  // Sayfa yüklendiğinde ve her 3 saniyede bir verileri güncelle
  useEffect(() => {
    verileriGetir();
    const interval = setInterval(verileriGetir, 3000);
    return () => clearInterval(interval);
  }, []);

  

  // CANLI GÜVENLİK ÖZETİ
  // Bu değerler mevcut log ve bağlantı verilerinden hesaplanır.
  // Veri yokken sahte sayı göstermek yerine "—" kullanılır.
  const logMetniOlustur = (log) =>
    `${log?.type || ''} ${log?.message || ''}`;

  const guvenlikOlaylari = sistemLoglari.filter((log) =>
    /(saldırı|attack|tehdit|threat|kritik|critical|alarm|brute|malware|şüpheli|suspicious|intrusion)/i.test(
      logMetniOlustur(log)
    )
  );

  const kritikOlaySayisi = sistemLoglari.filter((log) =>
    /(kritik|critical|yüksek|high|alarm|malware|intrusion)/i.test(
      logMetniOlustur(log)
    )
  ).length;

  const engellenenIpAdresleri = new Set();

  sistemLoglari.forEach((log) => {
    const logMetni = logMetniOlustur(log);

    if (/(engellendi|bloklandı|blocked|reddedildi|karantinaya alındı)/i.test(logMetni)) {
      const bulunanIpAdresleri =
        logMetni.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/g) || [];

      bulunanIpAdresleri.forEach((ipAdresi) =>
        engellenenIpAdresleri.add(ipAdresi)
      );
    }
  });

  const portSayilari = {};

  sistemLoglari.forEach((log) => {
    const logMetni = logMetniOlustur(log);
    const portDeseni =
      /(?:port|hedef port|destination port)\s*[:#-]?\s*(\d{1,5})/gi;

    let portEslesmesi;

    while ((portEslesmesi = portDeseni.exec(logMetni)) !== null) {
      const port = portEslesmesi[1];
      portSayilari[port] = (portSayilari[port] || 0) + 1;
    }
  });

  const enCokHedeflenenPort =
    Object.entries(portSayilari).sort((a, b) => b[1] - a[1])[0]?.[0] || '—';

  const sonGuvenlikOlayi =
    guvenlikOlaylari[guvenlikOlaylari.length - 1] ||
    sistemLoglari[sistemLoglari.length - 1];

  const sonOlayZamani = sonGuvenlikOlayi?.time || '—';

  const istatistikKartlari = [
    {
      baslik: 'Tespit Edilen Olay',
      deger: guvenlikOlaylari.length > 0 ? guvenlikOlaylari.length : '—',
      aciklama:
        guvenlikOlaylari.length > 0
          ? 'Sistem loglarından hesaplandı'
          : 'Henüz güvenlik olayı yok',
      ikonArkaPlan: 'bg-indigo-500/10',
      ikonRengi: 'text-indigo-300',
      kenarlik: 'border-indigo-500/15',
      ikonYolu:
        'M4 7h16M4 12h16M4 17h10'
    },
    {
      baslik: 'Kritik Olay',
      deger: kritikOlaySayisi > 0 ? kritikOlaySayisi : '—',
      aciklama:
        kritikOlaySayisi > 0
          ? 'Yüksek önem seviyeli kayıt'
          : 'Kritik kayıt bulunmuyor',
      ikonArkaPlan: 'bg-red-500/10',
      ikonRengi: 'text-red-300',
      kenarlik: 'border-red-500/15',
      ikonYolu:
        'M12 9v4m0 4h.01M10.3 4.3L2.8 17.4A2 2 0 004.5 20h15a2 2 0 001.7-2.6L13.7 4.3a2 2 0 00-3.4 0z'
    },
    {
      baslik: 'Engellenen IP',
      deger:
        engellenenIpAdresleri.size > 0
          ? engellenenIpAdresleri.size
          : '—',
      aciklama:
        engellenenIpAdresleri.size > 0
          ? 'Benzersiz engellenen adres'
          : 'Engelleme kaydı bulunmuyor',
      ikonArkaPlan: 'bg-amber-500/10',
      ikonRengi: 'text-amber-300',
      kenarlik: 'border-amber-500/15',
      ikonYolu:
        'M12 3l7 3v5c0 4.5-2.8 8.2-7 10-4.2-1.8-7-5.5-7-10V6l7-3zM9 9l6 6m0-6l-6 6'
    },
    {
      baslik: 'Hedeflenen Port',
      deger: enCokHedeflenenPort,
      aciklama:
        enCokHedeflenenPort !== '—'
          ? 'Loglarda en sık görülen port'
          : 'Port bilgisi bekleniyor',
      ikonArkaPlan: 'bg-cyan-500/10',
      ikonRengi: 'text-cyan-300',
      kenarlik: 'border-cyan-500/15',
      ikonYolu:
        'M8 7V3m8 4V3M5 11h14M7 11v9m10-9v9M4 7h16v13H4V7z'
    },
    {
      baslik: 'Son Olay Zamanı',
      deger: sonOlayZamani,
      aciklama:
        sonOlayZamani !== '—'
          ? 'En son alınan güvenlik kaydı'
          : 'Henüz zaman bilgisi yok',
      ikonArkaPlan: 'bg-violet-500/10',
      ikonRengi: 'text-violet-300',
      kenarlik: 'border-violet-500/15',
      ikonYolu:
        'M12 8v4l3 2M5.6 5.6a9 9 0 1012.8 0'
    },
    {
      baslik: 'ESP32 Durumu',
      deger:
        esp32Durumu === 'BAĞLANILIYOR...'
          ? 'Kontrol ediliyor'
          : esp32Durumu === 'ÇEVRİMİÇİ'
          ? 'Çevrimiçi'
          : 'Çevrimdışı',
      aciklama:
        esp32Durumu === 'ÇEVRİMİÇİ'
          ? `Aktif mod: ${
              aktifLed === 'blue'
                ? 'Mavi İzleme'
                : aktifLed === 'red'
                ? 'Kırmızı Alarm'
                : 'Normal'
            }`
          : 'Cihaz bağlantısı bekleniyor',
      ikonArkaPlan:
        esp32Durumu === 'ÇEVRİMİÇİ'
          ? 'bg-emerald-500/10'
          : 'bg-slate-700/40',
      ikonRengi:
        esp32Durumu === 'ÇEVRİMİÇİ'
          ? 'text-emerald-300'
          : 'text-slate-500',
      kenarlik:
        esp32Durumu === 'ÇEVRİMİÇİ'
          ? 'border-emerald-500/15'
          : 'border-slate-800',
      ikonYolu:
        'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 5h10a2 2 0 012 2v10a2 2 0 01-2 2H7a2 2 0 01-2-2V7a2 2 0 012-2zM9 9h6v6H9V9z'
    }
  ];

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-300 flex overflow-hidden font-sans">
      
      {/* SOL MENÜ (SIDEBAR) */}
      <aside className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col shadow-2xl z-20">
        <div className="p-6 border-b border-slate-800">
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-2">
            Cyber<span className="text-indigo-500">Hunter</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1 font-medium tracking-widest">KONTROL PANELİ</p>
        </div>

        <nav className="flex-1 p-4 flex flex-col gap-2">
          <button onClick={() => setAktifSayfa('bilgi')} className={`px-4 py-3 rounded-xl text-left font-medium transition-all flex items-center gap-3 ${aktifSayfa === 'bilgi' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-transparent'}`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            Sistem Bilgisi
          </button>
          
          {/* YENİ EKLENEN DONANIM KONTROLÜ SEKMESİ */}
          <button onClick={() => setAktifSayfa('kontrol')} className={`px-4 py-3 rounded-xl text-left font-medium transition-all flex items-center gap-3 ${aktifSayfa === 'kontrol' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.2)]' : 'hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-transparent'}`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
            Donanım Kontrolü
          </button>

          <button onClick={() => setAktifSayfa('grafik')} className={`px-4 py-3 rounded-xl text-left font-medium transition-all flex items-center gap-3 ${aktifSayfa === 'grafik' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-transparent'}`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"></path></svg>
            Canlı Sinyal Akışı
          </button>
          
          <button onClick={() => setAktifSayfa('loglar')} className={`px-4 py-3 rounded-xl text-left font-medium transition-all flex items-center gap-3 ${aktifSayfa === 'loglar' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-transparent'}`}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path></svg>
            Sistem Logları
          </button>
        </nav>

        <div className="p-4 border-t border-slate-800 bg-slate-900/50">
          <div className="flex items-center gap-3">
             <div className="w-9 h-9 rounded-full bg-indigo-900/50 text-indigo-400 flex items-center justify-center text-sm font-bold border border-indigo-500/30">
               Ö
             </div>
             <div>
               <div className="text-sm font-bold text-white">Ömer</div>
               <div className="text-xs text-emerald-400 flex items-center gap-1.5 mt-0.5">
                 <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                 Veritabanı Aktif
               </div>
             </div>
          </div>
        </div>
      </aside>

      {/* SAĞ İÇERİK ALANI */}
      <main className="flex-1 p-6 md:p-8 overflow-y-auto flex flex-col w-full h-full">
        
        {/* AKTİF SAYFA: DONANIM KONTROLÜ (YENİ) */}
        {aktifSayfa === 'kontrol' && (
          <div className="w-full flex-1 min-h-0 flex flex-col gap-6 animate-fade-in">
            
            <div className="flex justify-between items-center bg-slate-900 p-6 rounded-3xl border border-slate-800 shadow-lg">
              <div>
                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                  <svg className="w-6 h-6 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"></path></svg>
                  ESP32 Fiziksel Cihaz Kontrolü
                </h2>
                <p className="text-slate-500 text-sm mt-1">Cihaz Kimliği: <span className="font-mono text-indigo-400">esp32-led-01</span></p>
              </div>
              
              <div className="flex items-center gap-3 bg-slate-950 px-5 py-3 rounded-2xl border border-slate-800">
                <span className={`relative flex h-3 w-3`}>
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${esp32Durumu === 'ÇEVRİMİÇİ' ? 'bg-emerald-400' : 'bg-red-400'}`}></span>
                  <span className={`relative inline-flex rounded-full h-3 w-3 ${esp32Durumu === 'ÇEVRİMİÇİ' ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                </span>
                <span className="font-bold text-sm tracking-wide text-slate-300">
                  {esp32Durumu === 'ÇEVRİMİÇİ' ? 'BAĞLANTI AKTİF' : 'BAĞLANTI YOK'}
                </span>
              </div>
            </div>

            {/* GÖSTERGELER VE KONTROL PANELİ */}
            <div className="flex-1 min-h-[520px] flex flex-col md:flex-row gap-6">
              
              {/* Sol Taraf: Fiziksel Durum İzleme */}
              <div className="flex-1 bg-slate-900 rounded-3xl p-6 md:p-8 border border-slate-800 shadow-lg flex flex-col relative overflow-hidden">
                {/* Duruma göre çok hafif arka plan vurgusu */}
                <div
                  className={`pointer-events-none absolute inset-0 opacity-[0.06] blur-3xl transition-all duration-700 ${
                    aktifLed === 'red'
                      ? 'bg-red-500'
                      : aktifLed === 'blue'
                      ? 'bg-blue-500'
                      : 'bg-transparent'
                  }`}
                ></div>

                {/* Panel Başlığı */}
                <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-400">
                      Fiziksel durum izleme
                    </p>
                    <h3 className="mt-2 text-xl font-bold text-white">
                      Canlı Cihaz Durumu
                    </h3>
                    <p className="mt-1 text-sm text-slate-500">
                      ESP32 üzerindeki LED ve müdahale durumunu gerçek zamanlı izleyin.
                    </p>
                  </div>

                  <div
                    className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${
                      aktifLed === 'red'
                        ? 'border-red-400/25 bg-red-500/10 text-red-300'
                        : aktifLed === 'blue'
                        ? 'border-blue-400/25 bg-blue-500/10 text-blue-300'
                        : 'border-emerald-400/20 bg-emerald-500/10 text-emerald-300'
                    }`}
                  >
                    <span
                      className={`h-2 w-2 rounded-full ${
                        aktifLed === 'red'
                          ? 'bg-red-400'
                          : aktifLed === 'blue'
                          ? 'bg-blue-400'
                          : 'bg-emerald-400'
                      }`}
                    ></span>
                    {aktifLed === 'red'
                      ? 'ALARM MODU'
                      : aktifLed === 'blue'
                      ? 'İZLEME MODU'
                      : 'SİSTEM NORMAL'}
                  </div>
                </div>

                {/* LED Durum Kartları */}
                <div className="relative z-10 my-auto grid w-full grid-cols-1 gap-5 py-7 sm:grid-cols-2">
                  {/* MAVİ LED KARTI */}
                  <div
                    className={`rounded-2xl border p-5 md:p-6 transition-all duration-500 ${
                      aktifLed === 'blue'
                        ? 'border-blue-400/40 bg-blue-500/[0.08] shadow-[0_16px_40px_rgba(37,99,235,0.12)]'
                        : 'border-slate-800 bg-slate-950/45'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div
                        className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border transition-all duration-500 ${
                          aktifLed === 'blue'
                            ? 'border-blue-300/35 bg-blue-500/20 text-blue-200 shadow-[0_0_28px_rgba(59,130,246,0.22)]'
                            : 'border-slate-700 bg-slate-900 text-slate-600'
                        }`}
                      >
                        <svg
                          className="h-7 w-7"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="1.8"
                            d="M12 3l7 3v5c0 4.5-2.8 8.2-7 10-4.2-1.8-7-5.5-7-10V6l7-3z"
                          />
                        </svg>
                      </div>

                      <span
                        className={`rounded-full border px-2.5 py-1 text-[11px] font-bold tracking-wide ${
                          aktifLed === 'blue'
                            ? 'border-blue-400/25 bg-blue-500/15 text-blue-300'
                            : 'border-slate-700 bg-slate-900 text-slate-500'
                        }`}
                      >
                        {aktifLed === 'blue' ? 'AKTİF' : 'PASİF'}
                      </span>
                    </div>

                    <div className="mt-5">
                      <h4 className="text-base font-semibold text-slate-100">
                        Mavi İzleme
                      </h4>
                      <p className="mt-1.5 text-sm leading-6 text-slate-500">
                        Normal izleme ve güvenli takip senaryosunu temsil eder.
                      </p>
                    </div>

                    <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          aktifLed === 'blue'
                            ? 'w-full bg-blue-400'
                            : 'w-[8%] bg-slate-700'
                        }`}
                      ></div>
                    </div>
                  </div>

                  {/* KIRMIZI LED KARTI */}
                  <div
                    className={`rounded-2xl border p-5 md:p-6 transition-all duration-500 ${
                      aktifLed === 'red'
                        ? 'border-red-400/40 bg-red-500/[0.08] shadow-[0_16px_40px_rgba(220,38,38,0.12)]'
                        : 'border-slate-800 bg-slate-950/45'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div
                        className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border transition-all duration-500 ${
                          aktifLed === 'red'
                            ? 'border-red-300/35 bg-red-500/20 text-red-200 shadow-[0_0_28px_rgba(239,68,68,0.22)]'
                            : 'border-slate-700 bg-slate-900 text-slate-600'
                        }`}
                      >
                        <svg
                          className="h-7 w-7"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="1.8"
                            d="M18 8a6 6 0 10-12 0c0 7-3 7-3 7h18s-3 0-3-7M10 19h4"
                          />
                        </svg>
                      </div>

                      <span
                        className={`rounded-full border px-2.5 py-1 text-[11px] font-bold tracking-wide ${
                          aktifLed === 'red'
                            ? 'border-red-400/25 bg-red-500/15 text-red-300'
                            : 'border-slate-700 bg-slate-900 text-slate-500'
                        }`}
                      >
                        {aktifLed === 'red' ? 'AKTİF' : 'PASİF'}
                      </span>
                    </div>

                    <div className="mt-5">
                      <h4 className="text-base font-semibold text-slate-100">
                        Kırmızı Tehdit
                      </h4>
                      <p className="mt-1.5 text-sm leading-6 text-slate-500">
                        Alarm, tehdit ve fiziksel müdahale senaryosunu temsil eder.
                      </p>
                    </div>

                    <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          aktifLed === 'red'
                            ? 'w-full bg-red-400'
                            : 'w-[8%] bg-slate-700'
                        }`}
                      ></div>
                    </div>
                  </div>
                </div>

                {/* Alt Sistem Bilgileri */}
                <div className="relative z-10 grid grid-cols-2 gap-3 xl:grid-cols-4">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                      Aktif Mod
                    </p>
                    <p className="mt-1.5 text-sm font-semibold text-slate-200">
                      {aktifLed === 'blue'
                        ? 'Mavi İzleme'
                        : aktifLed === 'red'
                        ? 'Kırmızı Alarm'
                        : 'Normal'}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                      Cihaz Kimliği
                    </p>
                    <p className="mt-1.5 truncate font-mono text-sm text-indigo-400">
                      esp32-led-01
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                      Bağlantı
                    </p>
                    <p
                      className={`mt-1.5 text-sm font-semibold ${
                        esp32Durumu === 'ÇEVRİMİÇİ'
                          ? 'text-emerald-400'
                          : 'text-red-400'
                      }`}
                    >
                      {esp32Durumu}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                      Kontrol Türü
                    </p>
                    <p className="mt-1.5 text-sm font-semibold text-slate-200">
                      Uzaktan
                    </p>
                  </div>
                </div>
              </div>

              {/* Sağ Taraf: Uzaktan Müdahale Paneli */}
              <div className="w-full md:w-[380px] xl:w-[420px] shrink-0 bg-slate-900 rounded-3xl p-6 md:p-7 border border-slate-800 shadow-lg flex flex-col justify-between">
                <div>
                  <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                    <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
                    Uzaktan Müdahale
                  </h3>
                  <p className="text-sm text-slate-500 mb-8">ESP32 modülündeki donanımsal tepkileri doğrudan tetikleyin.</p>
                  
                  <div className="space-y-3">
  {/* MAVİ MOD BUTONU */}
  <button
    type="button"
    onClick={() => komutGonder('MAVI_YAK')}
    className="
      group w-full
      flex items-center gap-4
      rounded-xl border border-blue-400/25
      bg-gradient-to-r from-blue-600/25 to-blue-500/15
      px-5 py-3.5
      text-left
      shadow-[0_8px_24px_rgba(37,99,235,0.10)]
      transition-all duration-300
      hover:border-blue-400/45
      hover:from-blue-600/35 hover:to-blue-500/20
      hover:shadow-[0_10px_28px_rgba(37,99,235,0.16)]
      active:scale-[0.98]
    "
  >
    <div
      className="
        flex h-10 w-10 shrink-0 items-center justify-center
        rounded-lg border border-blue-300/20
        bg-blue-400/10 text-blue-200
        transition-colors duration-300
        group-hover:bg-blue-400/15
      "
    >
      <svg
        className="h-6 w-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.8"
          d="M12 3l7 3v5c0 4.5-2.8 8.2-7 10-4.2-1.8-7-5.5-7-10V6l7-3z"
        />
      </svg>
    </div>

    <div className="min-w-0">
      <div className="font-semibold text-slate-100">
        Mavi Renge Zorla
      </div>

      <div className="mt-0.5 text-xs text-blue-200/60">
        Mavi modu etkinleştir
      </div>
    </div>
  </button>

  {/* KIRMIZI ALARM BUTONU */}
  <button
    type="button"
    onClick={() => komutGonder('KIRMIZI_YAK')}
    className="
      group w-full
      flex items-center gap-4
      rounded-xl border border-red-400/25
      bg-gradient-to-r from-red-600/25 to-red-500/15
      px-5 py-3.5
      text-left
      shadow-[0_8px_24px_rgba(220,38,38,0.10)]
      transition-all duration-300
      hover:border-red-400/45
      hover:from-red-600/35 hover:to-red-500/20
      hover:shadow-[0_10px_28px_rgba(220,38,38,0.16)]
      active:scale-[0.98]
    "
  >
    <div
      className="
        flex h-10 w-10 shrink-0 items-center justify-center
        rounded-lg border border-red-300/20
        bg-red-400/10 text-red-200
        transition-colors duration-300
        group-hover:bg-red-400/15
      "
    >
      <svg
        className="h-6 w-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.8"
          d="M18 8a6 6 0 10-12 0c0 7-3 7-3 7h18s-3 0-3-7M10 19h4"
        />
      </svg>
    </div>

    <div className="min-w-0">
      <div className="font-semibold text-slate-100">
        Kırmızı Renge Zorla (Alarm)
      </div>

      <div className="mt-0.5 text-xs text-red-200/60">
        Alarm modunu etkinleştir
      </div>
    </div>
  </button>

  {/* NORMAL MOD BUTONU */}
  <button
    type="button"
    onClick={() => komutGonder('KAPAT')}
    className="
      group w-full
      flex items-center gap-4
      rounded-xl border border-slate-600/50
      bg-gradient-to-r from-slate-700/55 to-slate-800/60
      px-5 py-3.5
      text-left
      shadow-[0_8px_24px_rgba(0,0,0,0.10)]
      transition-all duration-300
      hover:border-slate-500/70
      hover:from-slate-700/70 hover:to-slate-800/75
      hover:shadow-[0_10px_28px_rgba(0,0,0,0.16)]
      active:scale-[0.98]
    "
  >
    <div
      className="
        flex h-10 w-10 shrink-0 items-center justify-center
        rounded-lg border border-slate-500/30
        bg-slate-400/10 text-slate-300
        transition-colors duration-300
        group-hover:bg-slate-400/15
      "
    >
      <svg
        className="h-6 w-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.8"
          d="M4 4v6h6M20 20v-6h-6M5.5 15a7 7 0 0011.5 2M18.5 9A7 7 0 007 7"
        />
      </svg>
    </div>

    <div className="min-w-0">
      <div className="font-semibold text-slate-100">
        Sistemi Normale Döndür (Kapat)
      </div>

      <div className="mt-0.5 text-xs text-slate-400">
        Normal modu geri yükle
      </div>
    </div>
  </button>
</div>
                </div>

                {/* Komut Geri Bildirim Alanı */}
                <div className="mt-6 h-8 flex items-center justify-center">
                  {komutDurumu && (
                    <span className="text-sm font-mono text-emerald-400 animate-pulse bg-emerald-950/50 px-4 py-1.5 rounded-full border border-emerald-900">
                      {komutDurumu}
                    </span>
                  )}
                </div>
              </div>

            </div>
          </div>
        )}

        {/* DİĞER SAYFALAR (Sistem Bilgisi, Grafik, Loglar) BURADA AYNEN KALIYOR... */}
        {/* AKTİF SAYFA: SİSTEM BİLGİSİ */}
        {aktifSayfa === 'bilgi' && (
          <div className="w-full flex flex-col gap-6 pb-8 animate-fade-in">

            {/* ÜRÜN TANITIM ALANI */}
            <section className="relative shrink-0 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 p-7 md:p-8 shadow-lg">
              <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-indigo-500/10 blur-3xl"></div>
              <div className="absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-cyan-500/5 blur-3xl"></div>

              <div className="relative z-10 grid gap-8 xl:grid-cols-[1.45fr_0.55fr] xl:items-center">
                <div>
                  <div className="mb-4 flex flex-wrap items-center gap-3">
                    <h1 className="text-3xl font-extrabold tracking-tight text-white md:text-4xl">
                      Cyber <span className="text-indigo-500">Hunter</span>
                    </h1>

                    <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold tracking-wider text-indigo-300">
                      v1.0
                    </span>
                  </div>

                  <h2 className="max-w-4xl text-xl font-semibold leading-relaxed text-slate-200 md:text-2xl">
                    Yapay zekâ destekli, siber istihbarat toplayan fiziksel honeypot ve aktif savunma sistemi
                  </h2>

                  <p className="mt-4 max-w-4xl text-sm leading-7 text-slate-400 md:text-base">
                    Gerçek bir sunucu gibi davranarak saldırganları kontrollü bir tuzak ortama çeker;
                    saldırı davranışlarını analiz eder, tehdit seviyesini sınıflandırır ve gerektiğinde
                    fiziksel donanım katmanında otomatik karşılık üretir.
                  </p>

                  <div className="mt-6 flex flex-wrap gap-3">
                    <span className="rounded-xl border border-indigo-500/20 bg-indigo-500/10 px-3.5 py-2 text-xs font-semibold text-indigo-300">
                      Fiziksel Honeypot
                    </span>
                    <span className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-3.5 py-2 text-xs font-semibold text-cyan-300">
                      Yapay Zekâ Analizi
                    </span>
                    <span className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3.5 py-2 text-xs font-semibold text-emerald-300">
                      Siber İstihbarat
                    </span>
                    <span className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-3.5 py-2 text-xs font-semibold text-amber-300">
                      Aktif Savunma
                    </span>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-700/70 bg-slate-950/70 p-5 shadow-inner">
                  <div className="mb-5 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                        Sistem Durumu
                      </p>
                      <p className="mt-1 text-lg font-bold text-white">Koruma Katmanı Aktif</p>
                    </div>

                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-300">
                      <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="1.8"
                          d="M12 3l7 3v5c0 4.5-2.8 8.2-7 10-4.2-1.8-7-5.5-7-10V6l7-3z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="1.8"
                          d="M9 12l2 2 4-4"
                        />
                      </svg>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between rounded-xl bg-slate-900 px-4 py-3">
                      <span className="text-sm text-slate-400">Bağlantı</span>
                      <span className={`flex items-center gap-2 text-sm font-semibold ${sunucuDurumu === 'ÇEVRİMİÇİ' ? 'text-emerald-400' : 'text-red-400'}`}>
                        <span className={`h-2 w-2 rounded-full ${sunucuDurumu === 'ÇEVRİMİÇİ' ? 'bg-emerald-400' : 'bg-red-400'}`}></span>
                        {sunucuDurumu}
                      </span>
                    </div>

                    <div className="flex items-center justify-between rounded-xl bg-slate-900 px-4 py-3">
                      <span className="text-sm text-slate-400">Cihaz</span>
                      <span className="font-mono text-sm font-semibold text-indigo-300">esp32-led-01</span>
                    </div>

                    <div className="flex items-center justify-between rounded-xl bg-slate-900 px-4 py-3">
                      <span className="text-sm text-slate-400">Çalışma Modu</span>
                      <span className="text-sm font-semibold text-slate-200">Hibrit Savunma</span>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* CANLI GÜVENLİK ÖZETİ */}
            <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-lg md:p-7">
              <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-400">
                    Canlı Güvenlik Özeti
                  </p>
                  <h3 className="mt-1 text-xl font-bold text-white">
                    Operasyonel sistem görünümü
                  </h3>
                  <p className="mt-2 text-sm text-slate-500">
                    Değerler mevcut loglar ve cihaz bağlantısından otomatik hesaplanır.
                  </p>
                </div>

                <div
                  className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${
                    sunucuDurumu === 'ÇEVRİMİÇİ'
                      ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
                      : sunucuDurumu === 'BAĞLANILIYOR...'
                      ? 'border-amber-500/20 bg-amber-500/10 text-amber-300'
                      : 'border-red-500/20 bg-red-500/10 text-red-300'
                  }`}
                >
                  <span
                    className={`h-2 w-2 rounded-full ${
                      sunucuDurumu === 'ÇEVRİMİÇİ'
                        ? 'bg-emerald-400'
                        : sunucuDurumu === 'BAĞLANILIYOR...'
                        ? 'bg-amber-400'
                        : 'bg-red-400'
                    }`}
                  ></span>
                  {sunucuDurumu}
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
                {istatistikKartlari.map((kart) => (
                  <div
                    key={kart.baslik}
                    className={`group rounded-2xl border bg-slate-950/55 p-5 transition-all duration-300 hover:-translate-y-0.5 hover:bg-slate-950/80 ${kart.kenarlik}`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div
                        className={`flex h-11 w-11 items-center justify-center rounded-xl ${kart.ikonArkaPlan} ${kart.ikonRengi}`}
                      >
                        <svg
                          className="h-5.5 w-5.5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="1.8"
                            d={kart.ikonYolu}
                          />
                        </svg>
                      </div>

                      <span className="h-2 w-2 rounded-full bg-slate-700 transition-colors group-hover:bg-indigo-400"></span>
                    </div>

                    <p className="mt-5 text-xs font-semibold uppercase tracking-[0.13em] text-slate-600">
                      {kart.baslik}
                    </p>

                    <p className="mt-2 break-words text-2xl font-extrabold text-white">
                      {kart.deger}
                    </p>

                    <p className="mt-2 min-h-10 text-xs leading-5 text-slate-500">
                      {kart.aciklama}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            {/* ÇALIŞMA PRENSİBİ VE TEKNOLOJİ SEVİYESİ */}
            <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
              <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-lg md:p-7">
                <div className="mb-6 flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-400">
                      Sistem Mimarisi
                    </p>
                    <h3 className="mt-1 text-xl font-bold text-white">CyberHunter Çalışma Prensibi</h3>
                  </div>

                  <span className="hidden rounded-full border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs font-medium text-slate-400 md:inline-flex">
                    Uçtan uca tehdit döngüsü
                  </span>
                </div>

                <div className="grid gap-3 md:grid-cols-5">
                  <div className="rounded-2xl border border-slate-700/70 bg-slate-950/70 p-4">
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-300">
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M4 7h16M4 12h16M4 17h10" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-white">Trafik Yakalama</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">Şüpheli istekler ve ağ hareketleri izlenir.</p>
                  </div>

                  <div className="rounded-2xl border border-slate-700/70 bg-slate-950/70 p-4">
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-300">
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M12 3l7 3v5c0 4-2.6 7.5-7 9-4.4-1.5-7-5-7-9V6l7-3z" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-white">Tuzak Ortamı</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">Saldırgan gerçek sistemde olduğunu düşünür.</p>
                  </div>

                  <div className="rounded-2xl border border-slate-700/70 bg-slate-950/70 p-4">
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10 text-violet-300">
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3M8 8h8v8H8z" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-white">AI Analizi</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">Davranışlar sınıflandırılır ve ilişkilendirilir.</p>
                  </div>

                  <div className="rounded-2xl border border-slate-700/70 bg-slate-950/70 p-4">
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-red-500/10 text-red-300">
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M12 9v4m0 4h.01M10.3 4.3L2.8 17.4A2 2 0 004.5 20h15a2 2 0 001.7-2.6L13.7 4.3a2 2 0 00-3.4 0z" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-white">Tehdit Kararı</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">Risk seviyesi belirlenir ve alarm üretilir.</p>
                  </div>

                  <div className="rounded-2xl border border-slate-700/70 bg-slate-950/70 p-4">
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-300">
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M5 12h14M12 5l7 7-7 7" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-white">Fiziksel Müdahale</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">Donanım üzerinden aktif savunma tetiklenir.</p>
                  </div>
                </div>
              </section>

              <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-lg md:p-7">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400">
                  Ürün Yol Haritası
                </p>
                <h3 className="mt-1 text-xl font-bold text-white">Teknoloji Hazırlık Seviyesi</h3>

                <div className="mt-7 flex items-end justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Mevcut seviye</p>
                    <p className="mt-1 text-4xl font-extrabold text-white">THS 4</p>
                  </div>

                  <svg className="mb-2 h-7 w-7 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M5 12h14M13 6l6 6-6 6" />
                  </svg>

                  <div className="text-right">
                    <p className="text-sm text-slate-500">Hedef seviye</p>
                    <p className="mt-1 text-4xl font-extrabold text-emerald-400">THS 8</p>
                  </div>
                </div>

                <div className="mt-6 h-2 overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full w-1/2 rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400"></div>
                </div>

                <p className="mt-5 text-sm leading-6 text-slate-400">
                  Hedef; prototip doğrulamasından gerçek operasyon ortamında çalışan, ölçeklenebilir ve
                  kritik altyapılara entegre edilebilir ürüne geçiştir.
                </p>
              </section>
            </div>

            {/* TEMEL YETENEKLER */}
            <section>
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-400">
                    Temel Yetenekler
                  </p>
                  <h3 className="mt-1 text-xl font-bold text-white">Sistemin öne çıkan savunma katmanları</h3>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
                  <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-300">
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M12 3l7 3v5c0 4.5-2.8 8.2-7 10-4.2-1.8-7-5.5-7-10V6l7-3z" />
                    </svg>
                  </div>
                  <h4 className="font-bold text-white">Hibrit Honeypot</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-500">Sanal tuzak yeteneklerini fiziksel cihaz tepkileriyle birleştirir.</p>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
                  <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-500/20 bg-cyan-500/10 text-cyan-300">
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M4 6h16M6 10h12M8 14h8M10 18h4" />
                    </svg>
                  </div>
                  <h4 className="font-bold text-white">Siber İstihbarat</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-500">Saldırı yöntemleri, komutlar ve davranış kalıpları kayıt altına alınır.</p>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
                  <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-red-500/20 bg-red-500/10 text-red-300">
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M12 8v4l3 2M5.6 5.6a9 9 0 1012.8 0" />
                    </svg>
                  </div>
                  <h4 className="font-bold text-white">Otomatik Karar</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-500">Tehdit seviyesine göre alarm ve fiziksel karşılık otomatik tetiklenir.</p>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
                  <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-300">
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" />
                    </svg>
                  </div>
                  <h4 className="font-bold text-white">Kesintisiz Çalışma</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-500">Enerji ve bağlantı kesintilerinde güvenlik sürekliliğini hedefler.</p>
                </div>
              </div>
            </section>

            {/* PROBLEM VE HEDEF KULLANICILAR */}
            <div className="grid gap-6 pb-2 xl:grid-cols-[1.05fr_0.95fr]">
              <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-lg md:p-7">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-400">
                  Çözdüğümüz Problem
                </p>
                <h3 className="mt-1 text-xl font-bold text-white">Neden CyberHunter?</h3>

                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  {[
                    'Siber saldırıların ve veri sızıntılarının hızla artması',
                    'Yalnızca yazılımsal honeypot çözümlerinin sınırlı kalması',
                    'Fiziksel savunma ve ağ müdahalesi mekanizmasının eksikliği',
                    'Elektrik ve bağlantı kesintilerinde güvenlik sürekliliği ihtiyacı'
                  ].map((problem, index) => (
                    <div key={index} className="flex gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                      <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-500/10 text-red-300">
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01" />
                        </svg>
                      </span>
                      <p className="text-sm leading-6 text-slate-400">{problem}</p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-lg md:p-7">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-400">
                  Kullanım Alanları
                </p>
                <h3 className="mt-1 text-xl font-bold text-white">Hedeflenen kurumlar</h3>

                <div className="mt-5 flex flex-wrap gap-3">
                  {[
                    'Savunma Sanayi',
                    'Devlet Kurumları',
                    'Finans ve Bankacılık',
                    'Sağlık Kuruluşları',
                    'Kritik Altyapılar',
                    'Endüstriyel Tesisler',
                    'Kurumsal Şirketler',
                    'Siber İstihbarat Ekipleri'
                  ].map((sector) => (
                    <span
                      key={sector}
                      className="rounded-xl border border-slate-700 bg-slate-950/70 px-3.5 py-2.5 text-sm font-medium text-slate-300 transition-colors hover:border-indigo-500/30 hover:text-indigo-300"
                    >
                      {sector}
                    </span>
                  ))}
                </div>

                <div className="mt-6 rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-4">
                  <p className="text-sm font-semibold text-indigo-300">Temel yaklaşım</p>
                  <p className="mt-1 text-sm leading-6 text-slate-400">
                    Sanal honeypotlarla oynanan oyunun kurallarını fiziksel yapı, yapay zekâ ve aktif savunma ile değiştirmek.
                  </p>
                </div>
              </section>
            </div>
          </div>
        )}

        {/* AKTİF SAYFA: GRAFİK */}
        {aktifSayfa === 'grafik' && (
          <div className="w-full h-full bg-slate-900 rounded-3xl p-8 border border-slate-800 shadow-lg flex flex-col animate-fade-in">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-xl font-bold text-white">Canlı Sinyal Akışı</h2>
              <span
  className={`text-sm font-semibold px-4 py-1.5 rounded-full border ${
    sunucuDurumu === 'ÇEVRİMDIŞI'
      ? 'text-red-400 bg-red-500/10 border-red-500/20'
      : grafikVerileri.length === 0
      ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
      : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
  }`}
>
  {sunucuDurumu === 'BAĞLANILIYOR...'
    ? 'Bağlanıyor' 
    : sunucuDurumu === 'ÇEVRİMDIŞI'
    ? 'Çevrimdışı'
    : grafikVerileri.length === 0
    ? 'Veri Bekleniyor'
    : 'Gerçek Zamanlı'}
</span>
            </div>
            <div className="flex-1 w-full h-full min-h-[400px]">
  {sunucuDurumu === 'BAĞLANILIYOR...' ? (
    <div className="h-full flex flex-col items-center justify-center text-center">
      <div className="h-12 w-12 rounded-full border-4 border-slate-800 border-t-indigo-500 animate-spin"></div>

      <h3 className="mt-5 text-base font-semibold text-slate-300">
        Sunucuya bağlanılıyor
      </h3>

      <p className="mt-2 text-sm text-slate-500">
        CyberHunter servisleri kontrol ediliyor.
      </p>
    </div>
  ) : sunucuDurumu === 'ÇEVRİMDIŞI' ? (
    <div className="h-full flex flex-col items-center justify-center text-center">
      <div className="w-16 h-16 rounded-2xl bg-slate-950 border border-red-500/20 flex items-center justify-center">
        <svg
          className="w-8 h-8 text-red-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.8"
            d="M12 9v4m0 4h.01M10.3 4.3L2.8 17.4A2 2 0 004.5 20h15a2 2 0 001.7-2.6L13.7 4.3a2 2 0 00-3.4 0z"
          />
        </svg>
      </div>

      <h3 className="mt-5 text-base font-semibold text-slate-300">
        Sunucu bağlantısı bulunamadı
      </h3>

      <p className="mt-2 max-w-md text-sm text-slate-500">
        Backend servisi çalıştırıldığında canlı sinyal verileri burada
        gösterilecektir.
      </p>

      <span className="mt-4 rounded-full border border-red-500/20 bg-red-500/10 px-4 py-1.5 text-xs font-semibold text-red-300">
        ÇEVRİMDIŞI
      </span>
    </div>
  ) : grafikVerileri.length === 0 ? (
    <div className="h-full flex flex-col items-center justify-center text-center">
      <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-indigo-500/20 bg-indigo-500/10">
        <span className="absolute h-3 w-3 rounded-full bg-indigo-400 animate-ping"></span>
        <span className="relative h-3 w-3 rounded-full bg-indigo-400"></span>
      </div>

      <h3 className="mt-5 text-base font-semibold text-slate-300">
        Canlı veri bekleniyor
      </h3>

      <p className="mt-2 max-w-md text-sm text-slate-500">
        Sunucu bağlantısı aktif ancak ESP32 tarafından henüz sinyal verisi
        gönderilmedi.
      </p>

      <span className="mt-4 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-4 py-1.5 text-xs font-semibold text-indigo-300">
        VERİ BEKLENİYOR
      </span>
    </div>
  ) : (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={grafikVerileri}
        margin={{
          top: 10,
          right: 30,
          bottom: 0,
          left: -10
        }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="#334155"
          vertical={false}
        />

        <XAxis
          dataKey="time"
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          dy={10}
        />

        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          dx={-10}
        />

        <Tooltip
          contentStyle={{
            backgroundColor: '#020617',
            borderRadius: '12px',
            border: '1px solid #1e293b',
            color: '#f8fafc',
            boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.5)'
          }}
          itemStyle={{
            color: '#e2e8f0',
            fontWeight: '500'
          }}
        />

        <Legend
          verticalAlign="top"
          height={40}
          iconType="circle"
          wrapperStyle={{
            fontSize: '14px',
            fontWeight: '500',
            color: '#94a3b8'
          }}
        />

        <Line
          type="monotone"
          name="ESP32 Gelen Sinyal"
          dataKey="gelenSinyal"
          stroke="#6366f1"
          strokeWidth={3}
          dot={{
            r: 4,
            strokeWidth: 2,
            fill: '#0f172a',
            stroke: '#6366f1'
          }}
          activeDot={{
            r: 7,
            strokeWidth: 0,
            fill: '#6366f1'
          }}
        />

        <Line
          type="monotone"
          name="Giden Komut"
          dataKey="gidenKomut"
          stroke="#10b981"
          strokeWidth={3}
          dot={{
            r: 4,
            strokeWidth: 2,
            fill: '#0f172a',
            stroke: '#10b981'
          }}
          activeDot={{
            r: 7,
            strokeWidth: 0,
            fill: '#10b981'
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  )}
</div>
          </div>
        )}

        {/* AKTİF SAYFA: LOGLAR */}
        {aktifSayfa === 'loglar' && (
          <div className="w-full h-full bg-slate-900 rounded-3xl p-8 border border-slate-800 shadow-lg flex flex-col animate-fade-in">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-white">Sistem Logları</h2>
              <div className="flex items-center gap-2">
                 <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse"></span>
                 <span className="text-sm font-semibold text-slate-400">Oturum Kaydediliyor...</span>
              </div>
            </div>
            <div className="flex-1 bg-slate-950 border border-slate-800/80 rounded-2xl p-6 overflow-y-auto font-mono text-sm leading-relaxed shadow-inner">
              {sistemLoglari.length > 0 ? (
                sistemLoglari.map((log, index) => (
                  <div key={index} className="mb-3 hover:bg-slate-800/50 p-1.5 rounded transition">
                    <span className="text-slate-500 mr-4">[{log.time}]</span> 
                    <span className="text-indigo-400 font-bold mr-3">[{log.type}]</span> 
                    <span className="text-slate-300">{log.message}</span>
                  </div>
                ))
              ) : (
                <div className="text-slate-500 text-center mt-10">Henüz bir log kaydı bulunmuyor veya sunucuya bağlanılamadı.</div>
              )}
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

export default App;