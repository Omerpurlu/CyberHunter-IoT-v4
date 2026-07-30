const nodes = [
  { title: 'Saldırı Verisi', tone: 'text-amber-300', icon: 'M4 7h16M4 12h10M4 17h7' },
  { title: 'Raspberry Pi Bridge', tone: 'text-rose-300', icon: 'M7 7h10v10H7zM9 3v4m6-4v4M9 17v4m6-4v4' },
  { title: 'SDA/SCL', tone: 'text-pink-300', icon: 'M5 8h14M5 16h14M8 5v6m8 2v6' },
  { title: 'ESP32 Risk Değerlendirmesi', tone: 'text-emerald-300', icon: 'M9 3v3m6-3v3M6 9H3m3 6H3m18-6h-3m3 6h-3M7 7h10v10H7z' },
  { title: 'HTTPS / ngrok', tone: 'text-violet-300', icon: 'M8 11V8a4 4 0 118 0v3m-9 0h10v9H7z' },
  { title: 'FastAPI', tone: 'text-indigo-300', icon: 'M13 2L5 14h6l-1 8 9-13h-6z' },
  { title: 'PostgreSQL', tone: 'text-cyan-300', icon: 'M5 6c0-2 3-3 7-3s7 1 7 3-3 3-7 3-7-1-7-3zm0 0v12c0 2 3 3 7 3s7-1 7-3V6' },
  { title: 'Dashboard', tone: 'text-blue-300', icon: 'M4 5h16v12H4zM9 21h6M12 17v4' },
];

export default function ArchitectureFlow() {
  return (
    <div className="architecture-flow" aria-label="CyberHunter uçtan uca veri akışı">
      {nodes.map((node, index) => (
        <div className="contents" key={node.title}>
          <div className="architecture-node">
            <div className={`architecture-node-icon ${node.tone}`}>
              <svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" d={node.icon} />
              </svg>
            </div>
            <span>{node.title}</span>
          </div>
          {index < nodes.length - 1 && (
            <div className="architecture-connector" aria-hidden="true">
              <span className="architecture-data-point" />
              <svg className="architecture-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

