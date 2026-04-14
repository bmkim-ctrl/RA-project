'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ImageViewer } from '@/components/ImageViewer';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ReportPanel } from '@/components/ReportPanel';
import { WorklistPanel } from '@/components/WorklistPanel';
import { PatientImage, PatientInfo, ViewerMode, WorklistEvent, apiClient } from '@/services/api';

export default function Home() {
  const [connected, setConnected] = useState(true);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [patients, setPatients] = useState<PatientInfo[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null);
  const [patientImages, setPatientImages] = useState<PatientImage[]>([]);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [diagnosis, setDiagnosis] = useState('uncertain');
  const [report, setReport] = useState('');
  const [viewerMode, setViewerMode] = useState<ViewerMode>('original');
  const [loading, setLoading] = useState(true);

  const fetchPatients = useCallback(async () => {
    try {
      const nextPatients = await apiClient.getPatients();
      setPatients(nextPatients);
      setSelectedPatient(current => {
        if (!current) {
          return nextPatients[0]?.patient_id ?? null;
        }
        const stillExists = nextPatients.some(patient => patient.patient_id === current);
        return stillExists ? current : nextPatients[0]?.patient_id ?? null;
      });
      setConnected(true);
      setBackendError(null);
    } catch (error) {
      setConnected(false);
      setBackendError(error instanceof Error ? error.message : 'Failed to load worklist');
    }
  }, []);

  const fetchPatientDetail = useCallback(async (patientId: string) => {
    try {
      const detail = await apiClient.getPatient(patientId);
      setPatientImages(detail.images);
      setSelectedImageIndex(current => Math.min(current, Math.max(detail.images.length - 1, 0)));
      const first = detail.images[0];
      setDiagnosis(first?.diagnosis || 'uncertain');
      setReport(first?.report || '');
    } catch (error) {
      setBackendError(error instanceof Error ? error.message : 'Failed to load patient');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPatients();
    apiClient.getHealth().catch(() => {
      setConnected(false);
      setBackendError('Backend connection unavailable');
      setLoading(false);
    });
  }, [fetchPatients]);

  useEffect(() => {
    if (selectedPatient) {
      setLoading(true);
      fetchPatientDetail(selectedPatient);
    } else {
      setLoading(false);
      setPatientImages([]);
      setDiagnosis('uncertain');
      setReport('');
    }
  }, [fetchPatientDetail, selectedPatient]);

  useEffect(() => {
    const current = patientImages[selectedImageIndex];
    if (!current) {
      setDiagnosis('uncertain');
      setReport('');
      return;
    }
    setDiagnosis(current.diagnosis || 'uncertain');
    setReport(current.report || '');
  }, [patientImages, selectedImageIndex]);

  useEffect(() => {
    const socket = new WebSocket(apiClient.getWebSocketUrl());
    socket.onmessage = event => {
      const payload = JSON.parse(event.data) as WorklistEvent;
      fetchPatients();
      if (selectedPatient && payload.patient_id === selectedPatient) {
        fetchPatientDetail(selectedPatient);
      }
    };
    socket.onerror = () => setBackendError('WebSocket disconnected');
    return () => socket.close();
  }, [fetchPatientDetail, fetchPatients, selectedPatient]);

  const generateReport = useCallback(async () => {
    const selectedImage = patientImages[selectedImageIndex];
    if (!selectedPatient || !selectedImage) return;
    try {
      const nextReport = await apiClient.generateReport(selectedPatient, selectedImage.filename);
      setReport(nextReport.report);
    } catch (error) {
      setBackendError(error instanceof Error ? error.message : 'Failed to generate report');
    }
  }, [patientImages, selectedImageIndex, selectedPatient]);

  const saveReading = useCallback(async () => {
    const selectedImage = patientImages[selectedImageIndex];
    if (!selectedPatient || !selectedImage) return;
    try {
      await apiClient.saveReading(selectedPatient, selectedImage.filename, diagnosis, report);
      await fetchPatientDetail(selectedPatient);
    } catch (error) {
      setBackendError(error instanceof Error ? error.message : 'Failed to save reading');
    }
  }, [diagnosis, fetchPatientDetail, patientImages, report, selectedImageIndex, selectedPatient]);

  const exportReport = useCallback(() => {
    const selectedImage = patientImages[selectedImageIndex];
    if (!selectedImage) return;
    const content = [
      `Patient: ${selectedPatient}`,
      `Image: ${selectedImage.filename}`,
      `Diagnosis: ${diagnosis}`,
      `Confidence: ${Math.round((selectedImage.confidence_score || 0) * 100)}%`,
      '',
      report,
    ].join('\n');

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${selectedPatient || 'patient'}_${selectedImage.filename}_report.txt`;
    link.click();
    URL.revokeObjectURL(link.href);
  }, [diagnosis, patientImages, report, selectedImageIndex, selectedPatient]);

  const selectedImage = useMemo(() => patientImages[selectedImageIndex], [patientImages, selectedImageIndex]);

  return (
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: 0 }}>
      <header style={{ padding: '14px 18px', borderBottom: '1px solid #16435a' }}>
        <div style={{ color: '#8fb7c9', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.8 }}>RA PACS Workflow</div>
        <h1 style={{ margin: '6px 0 0', fontSize: 26, fontWeight: 500 }}>AI-Assisted Rheumatoid Arthritis Reading</h1>
        <div style={{ color: '#8fb7c9', marginTop: 6, fontSize: 13 }}>Source folder: `RA/images/{'{patient_id}'}/*.png`</div>
        {!connected && <div style={{ color: '#ef4444', marginTop: 6 }}>{backendError}</div>}
      </header>

      {loading ? (
        <div style={{ padding: 24 }}>
          <LoadingSpinner message="Loading worklist..." />
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '280px minmax(0, 1fr) 280px',
            gap: 12,
            padding: 12,
            alignItems: 'stretch',
            height: 'calc(100vh - 88px)',
            overflow: 'hidden',
          }}
        >
          <WorklistPanel patients={patients} selectedPatient={selectedPatient} onSelectPatient={setSelectedPatient} />

          <div style={{ display: 'grid', gap: 12, height: '100%', minHeight: 0 }}>
            <div style={{ color: '#8fb7c9', fontSize: 12, padding: '2px 2px 0' }}>
              {selectedImage ? `${selectedImageIndex + 1} / ${patientImages.length} | ${selectedImage.filename}` : 'No image selected'}
            </div>

            <ImageViewer
              patientId={selectedPatient}
              images={patientImages}
              selectedIndex={selectedImageIndex}
              mode={viewerMode}
              onModeChange={setViewerMode}
              onNavigate={direction =>
                setSelectedImageIndex(current => {
                  if (patientImages.length === 0) return 0;
                  return direction === 'prev'
                    ? (current - 1 + patientImages.length) % patientImages.length
                    : (current + 1) % patientImages.length;
                })
              }
            />
          </div>

          <ReportPanel
            confidence={selectedImage?.confidence_score}
            diagnosis={diagnosis}
            report={report}
            warning={selectedImage?.warning}
            onDiagnosisChange={setDiagnosis}
            onReportChange={setReport}
            onGenerate={generateReport}
            onSave={saveReading}
            onExport={exportReport}
          />
        </div>
      )}
    </main>
  );
}
