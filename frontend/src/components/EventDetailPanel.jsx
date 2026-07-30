import { useEffect, useRef, useState } from 'react';
import StatusBadge from './StatusBadge';
import { tarihSaatFormatla } from '../utils/dateFormat';

function DetailField({ label, value, mono = false, copyable = false, onCopy }) {
  const displayed = value === null || value === undefined || value === '' ? 'Veri yok' : String(value);
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3.5">
      <dt className="text-xs font-medium text-slate-400">{label}</dt>
      <dd className="mt-1.5 flex min-w-0 items-start justify-between gap-2">
        <span className={`min-w-0 break-all text-sm font-semibold text-slate-200 ${mono ? 'font-mono' : ''}`}>{displayed}</span>
        {copyable && displayed !== 'Veri yok' && (
          <button type="button" aria-label={`${label} değerini kopyala`} onClick={() => onCopy(displayed)} className="min-h-8 shrink-0 rounded-lg border border-slate-700 px-2 text-xs text-slate-300 hover:bg-slate-800">
            Kopyala
          </button>
        )}
      </dd>
    </div>
  );
}

export default function EventDetailPanel({ event, onClose, returnFocus }) {
  const panelRef = useRef(null);
  const [copyMessage, setCopyMessage] = useState('');
  const assessment = event?.assessment;
  const eventId = event?.event_id;

  useEffect(() => {
    if (!eventId) return undefined;
    const closeButton = panelRef.current?.querySelector('button');
    closeButton?.focus();
    const onKeyDown = keyboardEvent => {
      if (keyboardEvent.key === 'Escape') {
        onClose();
        return;
      }
      if (keyboardEvent.key !== 'Tab') return;
      const focusable = panelRef.current?.querySelectorAll(
        'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (keyboardEvent.shiftKey && document.activeElement === first) {
        keyboardEvent.preventDefault();
        last.focus();
      } else if (!keyboardEvent.shiftKey && document.activeElement === last) {
        keyboardEvent.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      returnFocus?.();
    };
  }, [eventId, onClose, returnFocus]);

  if (!event) return null;

  const copy = async value => {
    try {
      await navigator.clipboard.writeText(value);
      setCopyMessage('Kopyalandı');
    } catch {
      setCopyMessage('Kopyalanamadı');
    }
  };

  const fields = [
    ['Event ID', event.event_id, true, true],
    ['Device ID', assessment?.device_id, true, true],
    ['Kaynak IP', event.source_ip, true, false],
    ['Port', event.destination_port, false, false],
    ['Protokol', event.protocol, false, false],
    ['Komut', event.command, true, true],
    ['Taktik', event.tactic, false, false],
    ['Olay tipi', event.event_type, false, false],
    ['Girdi risk skoru', event.input_risk_score, false, false],
    ['ESP32 risk skoru', assessment?.risk_score, false, false],
    ['ESP32 kararı', assessment?.decision, false, false],
    ['İşlenme durumu', assessment ? (assessment.processed ? 'İşlendi' : 'İşlenmedi') : 'Değerlendirme yok', false, false],
    ['Olay zamanı', tarihSaatFormatla(event.event_timestamp), false, false],
    ['Backend received_at', tarihSaatFormatla(event.received_at), false, false],
    ['Assessment zamanı', tarihSaatFormatla(assessment?.assessed_at), false, false],
    ['Assessment received_at', tarihSaatFormatla(assessment?.received_at), false, false],
  ];

  return (
    <div className="fixed inset-0 z-50">
      <button type="button" aria-label="Olay detayını kapat" onClick={onClose} className="absolute inset-0 h-full w-full bg-slate-950/75 backdrop-blur-sm" />
      <aside ref={panelRef} role="dialog" aria-modal="true" aria-labelledby="event-detail-title" className="event-detail-panel absolute inset-y-0 right-0 flex w-full max-w-xl flex-col border-l border-slate-700 bg-slate-900 shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-800 p-5 sm:p-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-400">Olay kaydı</p>
            <h2 id="event-detail-title" className="mt-1 text-xl font-bold text-white">Güvenlik Olayı Detayı</h2>
            {copyMessage && <p aria-live="polite" className="mt-1 text-xs text-slate-400">{copyMessage}</p>}
          </div>
          <button type="button" aria-label="Detay panelini kapat" onClick={onClose} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-800">×</button>
        </header>
        <div className="flex-1 overflow-y-auto p-5 sm:p-6">
          <div className="mb-5 flex flex-wrap gap-2">
            <StatusBadge status={assessment ? 'activity' : 'unknown'} label={assessment ? 'ESP32 değerlendirmesi var' : 'Değerlendirme yok'} />
          </div>
          <dl className="grid gap-3 sm:grid-cols-2">
            {fields.map(([label, value, mono, copyable]) => (
              <DetailField key={label} label={label} value={value} mono={mono} copyable={copyable} onCopy={copy} />
            ))}
          </dl>
        </div>
      </aside>
    </div>
  );
}
