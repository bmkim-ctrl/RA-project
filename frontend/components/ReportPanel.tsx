'use client';

import type { CSSProperties } from 'react';

import { ConfidenceBar } from './ConfidenceBar';
import { DiagnosisBox } from './DiagnosisBox';

export function ReportPanel({
  confidence,
  diagnosis,
  report,
  warning,
  onDiagnosisChange,
  onReportChange,
  onGenerate,
  onSave,
  onExport,
}: {
  confidence?: number | null;
  diagnosis: string;
  report: string;
  warning?: string | null;
  onDiagnosisChange: (value: string) => void;
  onReportChange: (value: string) => void;
  onGenerate: () => void;
  onSave: () => void;
  onExport: () => void;
}) {
  const hidden = (confidence ?? 0) < 0.3;
  const limited = (confidence ?? 0) < 0.5;

  return (
    <section style={panelStyle}>
      <div style={boxStyle}>
        <div style={boxHeaderStyle}>Confidence</div>
        <ConfidenceBar confidence={confidence} />
      </div>

      <div style={boxStyle}>
        <div style={boxHeaderStyle}>Diagnosis</div>
        {limited && (
          <div style={warningStyle}>
            {warning || 'AI confidence is limited. Review manually before finalizing the report.'}
          </div>
        )}
        <DiagnosisBox diagnosis={diagnosis} onChange={onDiagnosisChange} hidden={hidden} />
      </div>

      <div style={{ ...boxStyle, display: 'grid', gridTemplateRows: 'auto minmax(0, 1fr) auto' }}>
        <div style={boxHeaderStyle}>Report</div>
        <textarea value={report} onChange={event => onReportChange(event.target.value)} rows={16} style={textareaStyle} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginTop: 10 }}>
          <button onClick={onGenerate} style={buttonStyle}>Generate</button>
          <button onClick={onSave} style={buttonStyle}>Save</button>
          <button onClick={onExport} style={buttonStyle}>Export</button>
        </div>
      </div>
    </section>
  );
}

const panelStyle: CSSProperties = {
  display: 'grid',
  gap: 10,
  height: '100%',
  minHeight: 0,
  gridTemplateRows: '100px 120px minmax(0, 1fr)',
};

const boxStyle: CSSProperties = {
  background: '#111',
  border: '1px solid #16435a',
  padding: 12,
  minHeight: 0,
  overflow: 'hidden',
};

const boxHeaderStyle: CSSProperties = {
  background: '#1f6b8e',
  color: '#f7fbff',
  padding: '8px 10px',
  margin: '-12px -12px 12px',
  fontSize: 21,
  textAlign: 'center',
};

const warningStyle: CSSProperties = {
  padding: 8,
  marginBottom: 10,
  background: 'rgba(245, 158, 11, 0.12)',
  border: '1px solid rgba(245, 158, 11, 0.35)',
  color: '#f5d08a',
  fontSize: 12,
};

const textareaStyle: CSSProperties = {
  width: '100%',
  minHeight: 0,
  height: '100%',
  resize: 'vertical',
  border: '1px solid #16435a',
  background: '#031018',
  color: '#eaf2f9',
  padding: 12,
  lineHeight: 1.5,
  fontSize: 13,
};

const buttonStyle: CSSProperties = {
  border: '1px solid #16435a',
  background: '#1f6b8e',
  color: '#fff',
  padding: '8px 10px',
  fontWeight: 600,
  fontSize: 12,
};
