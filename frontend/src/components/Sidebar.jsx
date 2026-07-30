import { useEffect, useRef, useState } from 'react';

const menus = [
  ['bilgi', 'Sistem Bilgisi', 'M13 16h-1v-4h-1m1-4h.01'],
  ['kontrol', 'ESP32 Değerlendirmesi', 'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4'],
  ['saglik', 'Sistem Sağlığı', 'M4 13h4l2-7 4 12 2-5h4'],
  ['loglar', 'Güvenlik Olayları', 'M4 6h16M4 10h16M4 14h16M4 18h16'],
];

function SidebarContent({ aktifSayfa, onSelect, sunucuDurumu }) {
  const baglanti = sunucuDurumu === 'BAĞLANILIYOR...'
    ? { metin: 'Bağlantı Bekleniyor', renk: 'text-amber-300', nokta: 'bg-amber-400' }
    : sunucuDurumu === 'ÇEVRİMİÇİ'
      ? { metin: 'Bağlantı Sağlandı', renk: 'text-emerald-300', nokta: 'bg-emerald-400' }
      : { metin: 'Bağlantı Yok', renk: 'text-red-300', nokta: 'bg-red-400' };

  return (
    <>
      <div className="border-b border-slate-800 p-6">
        <h1 className="flex items-center gap-2 text-2xl font-extrabold tracking-tight text-white">
          Cyber<span className="text-indigo-500">Hunter</span>
        </h1>
        <p className="mt-1 text-xs font-medium tracking-widest text-slate-400">KONTROL PANELİ</p>
      </div>
      <nav aria-label="Ana navigasyon" className="flex flex-1 flex-col gap-2 p-4">
        {menus.map(([id, label, path]) => (
          <button
            key={id}
            type="button"
            aria-label={`${label} sayfasını aç`}
            aria-current={aktifSayfa === id ? 'page' : undefined}
            onClick={() => onSelect(id)}
            className={`flex min-h-11 items-center gap-3 rounded-xl border px-4 py-3 text-left font-medium transition-colors duration-150 ${
              aktifSayfa === id
                ? 'border-indigo-500/30 bg-indigo-500/20 text-indigo-300'
                : 'border-transparent text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
            }`}
          >
            <svg aria-hidden="true" className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d={path} />
            </svg>
            {label}
          </button>
        ))}
      </nav>
      <div className="border-t border-slate-800 bg-slate-900/50 p-4">
        <div className="flex items-center gap-3">
          <div aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-full border border-indigo-500/30 bg-indigo-900/50 text-sm font-bold text-indigo-300">Ö</div>
          <div>
            <div className="text-sm font-bold text-white">Ömer</div>
            <div className={`mt-0.5 flex items-center gap-1.5 text-xs ${baglanti.renk}`}>
              <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${baglanti.nokta}`} />
              {baglanti.metin}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default function Sidebar({ aktifSayfa, setAktifSayfa, sunucuDurumu }) {
  const [acik, setAcik] = useState(false);
  const menuButtonRef = useRef(null);
  const drawerRef = useRef(null);

  useEffect(() => {
    if (!acik) return undefined;

    const oncekiOdak = document.activeElement;
    const geriDonusOdak = oncekiOdak instanceof HTMLElement ? oncekiOdak : menuButtonRef.current;
    const drawer = drawerRef.current;
    const odaklanabilirler = drawer?.querySelectorAll(
      'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
    );
    odaklanabilirler?.[0]?.focus();

    const klavyeKontrolu = event => {
      if (event.key === 'Escape') {
        setAcik(false);
        return;
      }
      if (event.key !== 'Tab' || !odaklanabilirler?.length) return;
      const ilk = odaklanabilirler[0];
      const son = odaklanabilirler[odaklanabilirler.length - 1];
      if (event.shiftKey && document.activeElement === ilk) {
        event.preventDefault();
        son.focus();
      } else if (!event.shiftKey && document.activeElement === son) {
        event.preventDefault();
        ilk.focus();
      }
    };

    document.addEventListener('keydown', klavyeKontrolu);
    return () => {
      document.removeEventListener('keydown', klavyeKontrolu);
      geriDonusOdak?.focus();
    };
  }, [acik]);

  const sayfaSec = id => {
    setAktifSayfa(id);
    setAcik(false);
  };

  return (
    <>
      <aside className="hidden w-72 shrink-0 flex-col border-r border-slate-800 bg-slate-900 shadow-2xl md:flex">
        <SidebarContent aktifSayfa={aktifSayfa} onSelect={setAktifSayfa} sunucuDurumu={sunucuDurumu} />
      </aside>

      <div className="fixed inset-x-0 top-0 z-30 flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900/95 px-4 backdrop-blur md:hidden">
        <span className="text-lg font-extrabold text-white">Cyber<span className="text-indigo-500">Hunter</span></span>
        <button
          ref={menuButtonRef}
          type="button"
          aria-label="Ana menüyü aç"
          aria-expanded={acik}
          aria-controls="mobile-navigation"
          onClick={() => setAcik(true)}
          className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-slate-700 text-slate-200 hover:bg-slate-800"
        >
          <svg aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      <div
        aria-hidden={!acik}
        inert={!acik}
        className={`fixed inset-0 z-40 transition-opacity duration-150 md:hidden ${
          acik ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
        }`}
      >
          <button
            type="button"
            aria-label="Menüyü kapat"
            tabIndex={acik ? 0 : -1}
            className="absolute inset-0 h-full w-full bg-slate-950/75 backdrop-blur-sm"
            onClick={() => setAcik(false)}
          />
          <aside
            ref={drawerRef}
            id="mobile-navigation"
            aria-label="Mobil navigasyon"
            className={`relative flex h-full w-[min(18rem,85vw)] flex-col border-r border-slate-800 bg-slate-900 shadow-2xl transition-transform duration-200 ease-out ${
              acik ? 'translate-x-0' : '-translate-x-full'
            }`}
          >
            <button
              type="button"
              aria-label="Menüyü kapat"
              onClick={() => setAcik(false)}
              className="absolute right-3 top-3 z-10 inline-flex h-11 w-11 items-center justify-center rounded-xl text-slate-300 hover:bg-slate-800"
            >
              <svg aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <SidebarContent aktifSayfa={aktifSayfa} onSelect={sayfaSec} sunucuDurumu={sunucuDurumu} />
          </aside>
      </div>
    </>
  );
}
