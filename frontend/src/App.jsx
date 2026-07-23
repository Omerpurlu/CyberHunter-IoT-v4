import { useState } from 'react';
import Sidebar from './components/Sidebar';
import SystemInfoPage from './pages/SystemInfoPage';
import HardwareControlPage from './pages/HardwareControlPage';
import LiveSignalsPage from './pages/LiveSignalsPage';
import SystemLogsPage from './pages/SystemLogsPage';
import useCyberHunterData from './hooks/useCyberHunterData';

function App() {
  const [aktifSayfa, setAktifSayfa] = useState('kontrol');
  const cyberHunterData = useCyberHunterData();
  const sayfaGoster = () => {
    switch (aktifSayfa) {
      case 'bilgi': return <SystemInfoPage {...cyberHunterData} />;
      case 'grafik': return <LiveSignalsPage {...cyberHunterData} />;
      case 'loglar': return <SystemLogsPage {...cyberHunterData} />;
      default: return <HardwareControlPage {...cyberHunterData} />;
    }
  };
  return <div className="h-screen w-screen bg-slate-950 text-slate-300 flex overflow-hidden font-sans"><Sidebar aktifSayfa={aktifSayfa} setAktifSayfa={setAktifSayfa} sunucuDurumu={cyberHunterData.sunucuDurumu}/><main className="flex-1 p-6 md:p-8 overflow-y-auto flex flex-col w-full h-full">{sayfaGoster()}</main></div>;
}

export default App;
