import Modal from "../Modal";
import ExtractedTable from "../../upload/components/ExtractedTable";
import { useState, useEffect, useMemo } from "react";
import { Download, ExternalLink } from "lucide-react";
import dynamic from 'next/dynamic';

// Dynamically import PDFViewer to avoid SSR issues
const PDFViewer = dynamic(() => import('../upload/PDFViewer'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
        <p className="text-gray-600">Loading PDF viewer...</p>
      </div>
    </div>
  )
});

type Props = {
  statement: any;
  onClose: () => void;
};

export default function CompareModal({ statement, onClose }: Props) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Generate GCS signed URL
  useEffect(() => {
    const fetchPdfUrl = async () => {
      if (!statement?.gcs_key && !statement?.file_name) {
        console.error('❌ No gcs_key or file_name in statement:', statement);
        setLoading(false);
        return;
      }

      try {
        const gcsKey = statement.gcs_key || statement.file_name;
        console.log('🔍 Fetching PDF with gcs_key:', gcsKey);
        console.log('📄 Statement object:', statement);
        
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${apiUrl}/api/pdf-preview/?gcs_key=${encodeURIComponent(gcsKey)}`;
        console.log('🔗 PDF preview URL:', url);
        
        const response = await fetch(url, {
          credentials: 'include' // Include cookies for authentication
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('✅ PDF URL fetched successfully');
          setPdfUrl(data.url); // Use the signed GCS URL directly
        } else {
          const errorData = await response.json().catch(() => ({}));
          console.error('❌ Failed to fetch PDF:', {
            status: response.status,
            statusText: response.statusText,
            error: errorData,
            gcs_key: gcsKey
          });
          // Show user-friendly message if file not found
          if (response.status === 404) {
            console.warn('⚠️ PDF file not found in storage. This may be an old statement where the file was deleted.');
          }
        }
        setLoading(false);
      } catch (err) {
        console.error('❌ Error fetching PDF:', err);
        setLoading(false);
      }
    };

    fetchPdfUrl();
  }, [statement]);

  const handleDownload = () => {
    if (pdfUrl) {
      window.open(pdfUrl, '_blank');
    }
  };

  return (
    <Modal onClose={onClose}>
      <div className="flex flex-col h-full w-full max-h-full min-h-0 min-w-0">
        {/* Sticky Header */}
        <header className="sticky top-0 z-20 bg-white dark:bg-slate-800 shadow-lg rounded-t-2xl flex items-center justify-between px-6 py-5 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-md">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Compare Statement</h2>
              <p className="text-sm text-slate-600 dark:text-slate-400 font-medium">{statement.file_name}</p>
            </div>
          </div>
          <nav aria-label="PDF toolbar" className="flex gap-1">
            <button
              onClick={handleDownload}
              aria-label="Download PDF"
              className="p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
            >
              <Download size={20} />
            </button>
            <a
              href={pdfUrl || '#'}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open PDF in new tab"
              className="p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
            >
              <ExternalLink size={20} />
            </a>
          </nav>
        </header>
        {/* Card Layout - 30/70 Split matching UnifiedTableEditor */}
        <div className="flex-1 flex flex-col lg:flex-row gap-6 w-full h-full max-h-full min-h-0 min-w-0 bg-slate-50 dark:bg-slate-900 p-6 rounded-b-2xl">
          {/* PDF Card - 30% width */}
          <section className={`${isCollapsed ? 'w-0 hidden' : 'w-full lg:w-[30%]'} min-w-0 min-h-0 flex flex-col rounded-xl shadow-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 overflow-hidden flex-shrink-0 transition-all duration-300`}>
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center justify-center">
                  <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Loading PDF...</p>
                </div>
              </div>
            ) : pdfUrl ? (
              <div className="h-full w-full">
                <PDFViewer
                  fileUrl={pdfUrl}
                  isCollapsed={isCollapsed}
                  onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
                />
              </div>
            ) : (
              <div className="flex items-center justify-center h-full p-8">
                <div className="text-center max-w-md">
                  <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-xl flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">PDF Not Available</h3>
                  <p className="text-slate-500 dark:text-slate-400 text-sm">
                    The original PDF file for this statement is not available. This may be an older statement where the file storage was cleaned up.
                  </p>
                  <p className="text-slate-600 dark:text-slate-400 text-xs mt-3">
                    The extracted data is still available in the table on the right.
                  </p>
                </div>
              </div>
            )}
          </section>
          {/* Extracted Table Card - 70% width */}
          <section className={`${isCollapsed ? 'w-full' : 'w-full lg:w-[70%]'} min-w-0 min-h-0 flex flex-col rounded-xl shadow-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 overflow-hidden flex-shrink-0 transition-all duration-300`}>
            <div className="sticky top-0 z-10 bg-white dark:bg-slate-800 px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                  <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0V4a1 1 0 011-1h16a1 1 0 011 1v16a1 1 0 01-1 1H4a1 1 0 01-1-1z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-slate-800 dark:text-slate-200">
                  {statement.edited_tables && statement.edited_tables.length > 0 ? 'Formatted Table(s)' : 'Extracted Table(s)'}
                </h3>
              </div>
            </div>
            <div className="flex-1 min-h-0 min-w-0 overflow-auto">
              {(statement.edited_tables && statement.edited_tables.length > 0) || (statement.raw_data && statement.raw_data.length > 0) ? (
                <ExtractedTable tables={statement.edited_tables || statement.raw_data} />
              ) : (
                <div className="text-center py-16">
                  <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-xl flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0V4a1 1 0 011-1h16a1 1 0 011 1v16a1 1 0 01-1 1H4a1 1 0 01-1-1z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">No extracted data found</h3>
                  <p className="text-slate-500 dark:text-slate-400 text-sm">This statement doesn&apos;t have any processed data yet.</p>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </Modal>
  );
}