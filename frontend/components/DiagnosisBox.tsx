'use client';

import type { CSSProperties } from 'react';

const options = [
  'No active erosive change',
  'Mild synovitis pattern',
  'Suspicious erosive change',
  'Inflammatory arthritis pattern',
  'Manual review required',
];

export function DiagnosisBox({
  diagnosis,
  onChange,
  hidden,
}: {
  diagnosis: string;
  onChange: (value: string) => void;
  hidden: boolean;
}) {
  if (hidden) {
    return (
      <div style={warningStyle}>
        <strong>AI 결과 신뢰도 낮음</strong>
        <div style={{ color: 'var(--muted)', marginTop: 6 }}>confidence가 0.3 미만이므로 diagnosis를 숨겼습니다.</div>
      </div>
    );
  }

  return (
    <label style={{ display: 'grid', gap: 8 }}>
      <strong>Diagnosis</strong>
      <select value={diagnosis} onChange={event => onChange(event.target.value)} style={selectStyle}>
        {options.map(option => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

const selectStyle: CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: 12,
  border: '1px solid var(--line)',
  background: '#0b1220',
  color: 'var(--text)',
};

const warningStyle: CSSProperties = {
  borderRadius: 14,
  border: '1px solid rgba(239, 68, 68, 0.4)',
  background: 'rgba(239, 68, 68, 0.08)',
  padding: 14,
};
