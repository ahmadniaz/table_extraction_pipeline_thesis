'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';
import { cn } from '@/lib/utils';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface UploadedDocumentPayload {
  id: string;
  filename: string;
  complexity_tier: string;
  page_count: number | null;
  is_digital: boolean | null;
  uploaded_at: string;
}

interface Props {
  onUploaded: (doc: UploadedDocumentPayload) => void | Promise<void>;
}

export default function DocumentUploadZone({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(
    async (files: File[]) => {
      const file = files[0];
      if (!file) return;

      if (!file.name.toLowerCase().endsWith('.pdf')) {
        toast.error('Only PDF files are accepted');
        return;
      }

      setUploading(true);
      try {
        const form = new FormData();
        form.append('file', file);
        form.append('complexity_tier', 'medium');
        const { data } = await axios.post<UploadedDocumentPayload>(`${API}/api/documents/upload`, form);
        toast.success(`Uploaded "${file.name}"`);
        await onUploaded(data);
      } catch (err: unknown) {
        const ax = err as { response?: { data?: { detail?: string } } };
        toast.error(ax?.response?.data?.detail ?? 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [onUploaded]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: uploading,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        'flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-xl p-10 cursor-pointer transition-colors select-none',
        isDragActive
          ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
          : 'border-slate-300 dark:border-slate-600 hover:border-indigo-400 hover:bg-slate-50 dark:hover:bg-slate-800/50',
        uploading && 'opacity-60 pointer-events-none'
      )}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      ) : (
        <UploadCloud className="w-8 h-8 text-slate-400" />
      )}
      <div className="text-center">
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {isDragActive ? 'Drop PDF here' : 'Drag & drop a PDF, or click to browse'}
        </p>
        <p className="text-xs text-slate-400 mt-1">PDF files only</p>
      </div>
    </div>
  );
}
