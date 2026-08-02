import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import EventDetailPanel from '../components/EventDetailPanel';
import EventFilters from '../components/EventFilters';
import PageHeader from '../components/PageHeader';
import SecurityEventList from '../components/SecurityEventList';
import SecurityEventsTable from '../components/SecurityEventsTable';

const initialFilters = { search: '', protocol: '', eventType: '', decision: '', risk: '' };
const stateIcon = (
  <svg aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M4 6h16M4 11h16M4 16h10" />
  </svg>
);

function uniqueValues(events, getter) {
  return [...new Set(events.map(getter).filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), 'tr'));
}

export default function SecurityEventsPage({
  guvenlikOlaylari = [],
  guvenlikOlaylariYukleniyor = false,
  guvenlikOlaylariHatasi = null,
}) {
  const [filters, setFilters] = useState(initialFilters);
  const [selectedId, setSelectedId] = useState(null);
  const [highlightedIds, setHighlightedIds] = useState(new Set());
  const previousIdsRef = useRef(null);
  const rowRefs = useRef(new Map());
  const returnFocusRef = useRef(null);

  useEffect(() => {
    const currentIds = new Set(guvenlikOlaylari.map(event => event.event_id));
    if (previousIdsRef.current) {
      const newIds = new Set([...currentIds].filter(id => !previousIdsRef.current.has(id)));
      if (newIds.size) {
        setHighlightedIds(newIds);
        const timeout = window.setTimeout(() => setHighlightedIds(new Set()), 850);
        previousIdsRef.current = currentIds;
        return () => window.clearTimeout(timeout);
      }
    }
    previousIdsRef.current = currentIds;
    return undefined;
  }, [guvenlikOlaylari]);

  useEffect(() => {
    if (selectedId && !guvenlikOlaylari.some(event => event.event_id === selectedId)) {
      setSelectedId(null);
    }
  }, [guvenlikOlaylari, selectedId]);

  const options = useMemo(() => ({
    protocols: uniqueValues(guvenlikOlaylari, event => event.protocol),
    eventTypes: uniqueValues(guvenlikOlaylari, event => event.event_type),
    decisions: uniqueValues(guvenlikOlaylari, event => event.assessment?.decision),
  }), [guvenlikOlaylari]);

  const filteredEvents = useMemo(() => {
    const query = filters.search.trim().toLocaleLowerCase('tr-TR');
    return guvenlikOlaylari.filter(event => {
      const assessment = event.assessment;
      const searchValues = [
        event.source_ip,
        event.event_id,
        event.event_type,
        event.command,
        event.tactic,
        assessment?.device_id,
      ].map(value => String(value ?? '').toLocaleLowerCase('tr-TR'));
      if (query && !searchValues.some(value => value.includes(query))) return false;
      if (filters.protocol && event.protocol !== filters.protocol) return false;
      if (filters.eventType && event.event_type !== filters.eventType) return false;
      if (filters.decision && assessment?.decision !== filters.decision) return false;
      if (filters.risk) {
        const risk = assessment?.risk_score;
        if (filters.risk === 'none') return risk === null || risk === undefined;
        const number = Number(risk);
        if (!Number.isFinite(number)) return false;
        if (filters.risk === 'low' && !(number < 45)) return false;
        if (filters.risk === 'medium' && !(number >= 45 && number < 75)) return false;
        if (filters.risk === 'high' && !(number >= 75)) return false;
      }
      return true;
    });
  }, [filters, guvenlikOlaylari]);

  const selectedEvent = selectedId
    ? guvenlikOlaylari.find(event => event.event_id === selectedId) || null
    : null;

  const selectEvent = event => {
    returnFocusRef.current = document.activeElement;
    setSelectedId(event.event_id);
  };
  const closePanel = useCallback(() => setSelectedId(null), []);
  const returnFocus = useCallback(() => {
    const target = rowRefs.current.get(selectedId) || returnFocusRef.current;
    target?.focus();
  }, [selectedId]);

  let content;
  if (guvenlikOlaylariYukleniyor) {
    content = <EmptyState icon={stateIcon} title="Güvenlik olayları yükleniyor" description="Güncel security-events kayıtları alınıyor." />;
  } else if (guvenlikOlaylariHatasi) {
    content = <ErrorState icon={stateIcon} title="Güvenlik olayları alınamadı" description={guvenlikOlaylariHatasi} />;
  } else if (!guvenlikOlaylari.length) {
    content = <EmptyState icon={stateIcon} title="Henüz güvenlik olayı yok" description="İlk olay alındığında güvenlik geçmişi burada gösterilecek." />;
  } else {
    content = (
      <>
        <EventFilters
          filters={filters}
          onChange={setFilters}
          onClear={() => setFilters(initialFilters)}
          protocols={options.protocols}
          eventTypes={options.eventTypes}
          decisions={options.decisions}
        />
        {!filteredEvents.length ? (
          <EmptyState icon={stateIcon} title="Filtreye uygun kayıt yok" description="Arama ölçütlerini değiştirin veya filtreleri temizleyin." />
        ) : (
          <>
            <SecurityEventsTable
              events={filteredEvents}
              selectedId={selectedId}
              highlightedIds={highlightedIds}
              onSelect={selectEvent}
              rowRefs={rowRefs}
            />
            <SecurityEventList
              events={filteredEvents}
              selectedId={selectedId}
              highlightedIds={highlightedIds}
              onSelect={selectEvent}
              rowRefs={rowRefs}
            />
          </>
        )}
      </>
    );
  }

  return (
    <div className="flex w-full flex-col gap-5 pb-4 animate-fade-in sm:gap-6">
      <PageHeader
        eyebrow="OLAY GEÇMİŞİ"
        title="Güvenlik Olayları"
        description="Raspberry Pi ve ESP32 tarafından işlenen güncel güvenlik olayları."
        meta={(
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
            <p className="text-xs font-medium text-slate-400">Gösterilen kayıt</p>
            <p className="mt-1 text-xl font-bold text-white">{guvenlikOlaylari.length}</p>
          </div>
        )}
      />
      {content}
      <EventDetailPanel event={selectedEvent} onClose={closePanel} returnFocus={returnFocus} />
    </div>
  );
}
