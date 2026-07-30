export default function EventFilters({
  filters,
  onChange,
  onClear,
  protocols,
  eventTypes,
  decisions,
}) {
  const update = (key, value) => onChange({ ...filters, [key]: value });
  const selectClass = 'min-h-11 rounded-xl border border-slate-700 bg-slate-950/70 px-3 text-sm text-slate-200 outline-none focus:border-indigo-400';

  return (
    <section aria-label="Olay filtreleri" className="rounded-3xl border border-slate-800 bg-slate-900/80 p-4 shadow-lg shadow-black/10">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(220px,1.5fr)_repeat(4,minmax(130px,1fr))_auto]">
        <label className="sr-only" htmlFor="event-search">Genel arama</label>
        <input
          id="event-search"
          type="search"
          value={filters.search}
          onChange={event => update('search', event.target.value)}
          placeholder="IP, Event ID, olay tipi, komut ara..."
          className={`${selectClass} px-4 sm:col-span-2 xl:col-span-1`}
        />
        <FilterSelect label="Protokol" value={filters.protocol} options={protocols} onChange={value => update('protocol', value)} className={selectClass} />
        <FilterSelect label="Olay tipi" value={filters.eventType} options={eventTypes} onChange={value => update('eventType', value)} className={selectClass} />
        <FilterSelect label="Karar" value={filters.decision} options={decisions} onChange={value => update('decision', value)} className={selectClass} />
        <FilterSelect
          label="Risk"
          value={filters.risk}
          options={[
            { value: 'low', label: '0–44' },
            { value: 'medium', label: '45–74' },
            { value: 'high', label: '75–100' },
            { value: 'none', label: 'Değerlendirme yok' },
          ]}
          onChange={value => update('risk', value)}
          className={selectClass}
        />
        <button type="button" onClick={onClear} className="min-h-11 rounded-xl border border-slate-700 px-4 text-sm font-semibold text-slate-300 transition-colors duration-150 hover:border-slate-600 hover:bg-slate-800">
          Filtreleri temizle
        </button>
      </div>
    </section>
  );
}

function FilterSelect({ label, value, options, onChange, className }) {
  const id = `filter-${label.toLocaleLowerCase('tr-TR').replaceAll(' ', '-')}`;
  return (
    <div>
      <label className="sr-only" htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={event => onChange(event.target.value)} className={`${className} w-full`}>
        <option value="">{label}: Tümü</option>
        {options.map(option => {
          const valueAndLabel = typeof option === 'string' ? { value: option, label: option } : option;
          return <option value={valueAndLabel.value} key={valueAndLabel.value}>{valueAndLabel.label}</option>;
        })}
      </select>
    </div>
  );
}
