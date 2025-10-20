/**
 * Document Types for PDF Preview
 */

export interface DocumentData {
  gcs_key?: string;
  file_name?: string;
  fileName?: string;
  upload_id?: string;
  id?: string;
  document_metadata?: {
    carrier_name?: string;
    carrier_confidence?: number;
    statement_date?: string;
    date_confidence?: number;
    broker_company?: string;
    document_type?: string;
  };
}

export interface DocumentPreviewState {
  pdfUrl: string | null;
  isLoading: boolean;
  error: boolean;
  errorMessage: string;
  retryCount: number;
  zoom: number;
}

export interface DocumentPreviewActions {
  loadPdf: () => Promise<void>;
  retry: () => void;
  download: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  setZoom: (zoom: number) => void;
}

export interface DocumentPreviewProps {
  uploaded: DocumentData;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

