import axios, { AxiosInstance } from 'axios';

export type PatientStatus = 'NEW' | 'READING' | 'DONE';
export type ViewerMode = 'original' | 'detection' | 'gradcam' | 'overlay';

export interface PatientInfo {
  patient_id: string;
  image_count: number;
  status: PatientStatus;
}

export interface PatientImage {
  filename: string;
  url: string;
  has_analysis: boolean;
  confidence_score?: number | null;
  diagnosis?: string | null;
  detection_image?: string | null;
  gradcam_image?: string | null;
  report?: string | null;
  warning?: string | null;
  last_updated?: string | null;
}

export interface PatientDetail {
  patient_id: string;
  status: PatientStatus;
  images: PatientImage[];
}

export interface ReportResponse {
  report: string;
  truncated: boolean;
  warning: string | null;
}

export interface WorklistEvent {
  event: 'bootstrap' | 'new_image' | 'analysis_complete' | 'reading_saved' | 'image_deleted' | 'patient_deleted';
  patient_id: string;
  filename?: string | null;
  status?: PatientStatus | null;
}

class APIClient {
  private client: AxiosInstance;
  readonly apiUrl: string;

  constructor() {
    this.apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.client = axios.create({
      baseURL: this.apiUrl,
      timeout: 30000,
    });
  }

  async getHealth() {
    const response = await this.client.get('/health');
    return response.data as { status: string; service: string };
  }

  async getPatients() {
    const response = await this.client.get('/patients');
    return response.data.patients as PatientInfo[];
  }

  async getPatient(patientId: string) {
    const response = await this.client.get(`/patients/${encodeURIComponent(patientId)}`);
    return response.data as PatientDetail;
  }

  async generateReport(patientId: string, filename: string) {
    const response = await this.client.post(`/patients/${encodeURIComponent(patientId)}/report/generate`, { filename });
    return response.data as ReportResponse;
  }

  async saveReading(patientId: string, filename: string, diagnosis: string, report: string) {
    const response = await this.client.post(`/patients/${encodeURIComponent(patientId)}/reading`, {
      filename,
      diagnosis,
      report,
    });
    return response.data as { message: string };
  }

  getImageUrl(patientId: string, filename: string) {
    return `${this.apiUrl}/patients/${encodeURIComponent(patientId)}/images/${encodeURIComponent(filename)}`;
  }

  getWebSocketUrl() {
    const url = new URL(this.apiUrl);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}/ws`;
  }
}

export const apiClient = new APIClient();
