const buttonStyles = {
  MAVI_YAK: {
    button: 'border-blue-500/30 bg-blue-500/5 hover:border-blue-400/60 hover:bg-blue-500/10',
    icon: 'border-blue-500/30 bg-blue-500/10 text-blue-400',
    active: 'ring-1 ring-blue-400/60 bg-blue-500/15',
    text: 'text-blue-200/60',
    path: 'M12 3l7 3v5c0 4.5-2.8 8.2-7 10-4.2-1.8-7-5.5-7-10V6l7-3z'
  },
  KIRMIZI_YAK: {
    button: 'border-red-500/30 bg-red-500/5 hover:border-red-400/60 hover:bg-red-500/10',
    icon: 'border-red-500/30 bg-red-500/10 text-red-400',
    active: 'ring-1 ring-red-400/60 bg-red-500/15',
    text: 'text-red-200/60',
    path: 'M18 8a6 6 0 10-12 0c0 7-3 7-3 7h18s-3 0-3-7M10 19h4'
  },
  KAPAT: {
    button: 'border-emerald-500/30 bg-emerald-500/5 hover:border-emerald-400/60 hover:bg-emerald-500/10',
    icon: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
    active: 'ring-1 ring-emerald-400/60 bg-emerald-500/15',
    text: 'text-emerald-200/60',
    path: 'M4 4v6h6M20 20v-6h-6M5.5 15a7 7 0 0011.5 2M18.5 9A7 7 0 007 7'
  }
};

export default function RemoteControlPanel({ komutGonder, komutDurumu, aktifLed }) {
  const activeCommand = aktifLed === 'blue' ? 'MAVI_YAK' : aktifLed === 'red' ? 'KIRMIZI_YAK' : 'KAPAT';
  const button = (komut, baslik, aciklama) => {
    const style = buttonStyles[komut];
    return <button type="button" onClick={() => komutGonder(komut)} className={`group w-full flex items-center gap-4 rounded-xl border px-5 py-3.5 text-left shadow-[0_8px_24px_rgba(0,0,0,0.10)] transition-all duration-300 active:scale-[0.98] ${style.button} ${activeCommand === komut ? style.active : ''}`}><div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${style.icon}`}><svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d={style.path}/></svg></div><div className="min-w-0"><div className="font-semibold text-slate-100">{baslik}</div><div className={`mt-0.5 text-xs ${style.text}`}>{aciklama}</div></div></button>;
  };
  return <div className="w-full md:w-[380px] xl:w-[420px] shrink-0 bg-slate-900 rounded-3xl p-6 md:p-7 border border-slate-800 shadow-lg flex flex-col justify-between"><div><h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">Uzaktan Müdahale</h3><p className="text-sm text-slate-500 mb-8">ESP32 modülündeki donanımsal tepkileri doğrudan tetikleyin.</p><div className="space-y-3">{button('MAVI_YAK','Mavi Renge Zorla','Mavi modu etkinleştir')}{button('KIRMIZI_YAK','Kırmızı Renge Zorla (Alarm)','Alarm modunu etkinleştir')}{button('KAPAT','Sistemi Normale Döndür (Kapat)','Normal modu geri yükle')}</div></div><div className="mt-6 h-8 flex items-center justify-center">{komutDurumu && <span className="text-sm font-mono text-emerald-400 animate-pulse bg-emerald-950/50 px-4 py-1.5 rounded-full border border-emerald-900">{komutDurumu}</span>}</div></div>;
}
