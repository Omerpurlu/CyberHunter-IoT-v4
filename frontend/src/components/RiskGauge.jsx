export default function RiskGauge({ value }) {
  const hasValue = value !== null && value !== undefined && value !== '';
  const numericValue = hasValue ? Number(value) : null;
  const validValue = Number.isFinite(numericValue);
  const clamped = validValue ? Math.min(100, Math.max(0, numericValue)) : 0;
  const color = clamped >= 75 ? '#fb7185' : clamped >= 45 ? '#fbbf24' : '#34d399';

  return (
    <div
      className="risk-gauge"
      style={{ '--risk-value': `${clamped * 3.6}deg`, '--risk-color': color }}
      aria-label={validValue ? `ESP32 risk skoru ${numericValue} / 100` : 'ESP32 risk skoru veri yok'}
    >
      <div className="risk-gauge-content">
        <strong>{validValue ? numericValue : '—'}</strong>
        <span>/ 100</span>
      </div>
    </div>
  );
}

