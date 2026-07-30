import { useState } from 'react';
import Sidebar from './components/Sidebar';
import SystemInfoPage from './pages/SystemInfoPage';
import HardwareControlPage from './pages/HardwareControlPage';
import SystemLogsPage from './pages/SystemLogsPage';
import SystemHealthPage from './pages/SystemHealthPage';
import useCyberHunterData from './hooks/useCyberHunterData';

function App() {
  const [aktifSayfa, setAktifSayfa] = useState('bilgi');
  const cyberHunterData = useCyberHunterData();
  const sayfaGoster = () => {
    switch (aktifSayfa) {
      case 'kontrol': return <HardwareControlPage {...cyberHunterData} />;
      case 'loglar': return <SystemLogsPage {...cyberHunterData} />;
      case 'saglik': return <SystemHealthPage sistemSagligi={cyberHunterData.sistemSagligi} sonYenilemeZamani={cyberHunterData.sonYenilemeZamani} />;
      case 'bilgi':
      default: return <SystemInfoPage {...cyberHunterData} />;
    }
  };
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 font-sans text-slate-300">
      <Sidebar
        aktifSayfa={aktifSayfa}
        setAktifSayfa={setAktifSayfa}
        sunucuDurumu={cyberHunterData.sunucuDurumu}
      />
      <main className="h-full min-w-0 flex-1 overflow-y-auto px-4 pb-6 pt-20 sm:px-5 md:px-6 md:py-6 lg:px-8 lg:py-8">
        <div className="mx-auto flex min-h-full w-full max-w-[1440px] flex-col">
          {sayfaGoster()}
        </div>
      </main>
    </div>
  );
}

export default App;
