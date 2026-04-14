'use client';

export function ConfidenceBar({ confidence = 0 }: { confidence?: number | null }) {
  const value = Math.max(0, Math.min(1, confidence ?? 0));
  const color = value < 0.3 ? 'var(--danger)' : value < 0.5 ? 'var(--warn)' : 'var(--accent)';

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <strong>Confidence</strong>
        <span style={{ color }}>{Math.round(value * 100)}%</span>
      </div>
      <div style={{ height: 12, background: '#0b1220', borderRadius: 999, overflow: 'hidden', border: '1px solid var(--line)' }}>
        <div style={{ width: `${value * 100}%`, height: '100%', background: color, transition: 'width 180ms ease' }} />
      </div>
    </div>
  );
}
