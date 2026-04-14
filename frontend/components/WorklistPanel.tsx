'use client';

import type { CSSProperties } from 'react';

import { PatientInfo } from '@/services/api';

const statusColors: Record<PatientInfo['status'], string> = {
  NEW: '#7c8798',
  READING: '#f59e0b',
  DONE: '#22c55e',
};

export function WorklistPanel({
  patients,
  selectedPatient,
  onSelectPatient,
}: {
  patients: PatientInfo[];
  selectedPatient: string | null;
  onSelectPatient: (patientId: string) => void;
}) {
  return (
    <section style={panelStyle}>
      <div style={headerBoxStyle}>
        <div style={{ fontSize: 24, fontWeight: 600 }}>Patient List</div>
      </div>

      <div style={listStyle}>
        {patients.length === 0 ? (
          <div style={emptyStyle}>Patients appear automatically when new PNG studies are added under `RA/images`.</div>
        ) : (
          patients.map(patient => {
            const selected = patient.patient_id === selectedPatient;
            return (
              <button
                key={patient.patient_id}
                onClick={() => onSelectPatient(patient.patient_id)}
                style={{
                  ...itemStyle,
                  background: selected ? '#143e53' : 'transparent',
                  borderLeftColor: selected ? '#4fb0d4' : 'transparent',
                }}
              >
                <div style={{ display: 'grid', gap: 4 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                      <span style={{ color: '#8fb7c9', fontSize: 12 }}>[DIR]</span>
                      <strong style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{patient.patient_id}</strong>
                    </div>
                    <span style={{ color: statusColors[patient.status], fontSize: 12, fontWeight: 700 }}>{patient.status}</span>
                  </div>
                  <div style={{ color: '#9fb0bf', fontSize: 12, paddingLeft: 42 }}>{patient.image_count} images</div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}

const panelStyle: CSSProperties = {
  background: '#111',
  border: '1px solid #16435a',
  height: '100%',
  minHeight: 0,
  display: 'grid',
  gridTemplateRows: 'auto 1fr',
  overflow: 'hidden',
};

const headerBoxStyle: CSSProperties = {
  background: '#1f6b8e',
  color: '#f7fbff',
  padding: '14px 16px',
  borderBottom: '1px solid #16435a',
};

const listStyle: CSSProperties = {
  display: 'grid',
  gap: 2,
  padding: 8,
  overflowY: 'auto',
  minHeight: 0,
  alignContent: 'start',
};

const itemStyle: CSSProperties = {
  width: '100%',
  textAlign: 'left',
  color: '#e5eef6',
  border: '1px solid transparent',
  borderLeftWidth: 3,
  padding: '9px 8px',
};

const emptyStyle: CSSProperties = {
  color: '#b2c1cf',
  lineHeight: 1.6,
  padding: 12,
  border: '1px dashed #16435a',
};
