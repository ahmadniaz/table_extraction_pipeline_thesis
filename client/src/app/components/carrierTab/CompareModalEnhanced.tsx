'use client'
import React, { useState, useEffect, useCallback } from 'react';
import { X, Database, Table, Download, Eye, FileText, ZoomIn, ZoomOut, ExternalLink } from 'lucide-react';
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

interface TableData {
  header: string[];
  rows: string[][];
  name?: string;
  id?: string;
  extractor?: string;
  metadata?: {
    extraction_method?: string;
    [key: string]: any;
  };
}


interface CompareModalEnhancedProps {
  statement: any;
  onClose: () => void;
}

export default function CompareModalEnhanced({ statement, onClose }: CompareModalEnhancedProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [tables, setTables] = useState<TableData[]>([]);
  const [currentTableIndex, setCurrentTableIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Load PDF URL with enhanced debugging
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

  // Load tables
  useEffect(() => {
    if (statement) {
      const tableData = statement.edited_tables || statement.raw_data || [];
      if (Array.isArray(tableData) && tableData.length > 0) {
        setTables(tableData);
        setCurrentTableIndex(0);
      } else {
        setTables([]);
        setError('No table data available for this statement');
      }
    }
  }, [statement]);

  const currentTable = tables[currentTableIndex];

  const downloadCSV = (table: TableData) => {
    const csvContent = [
      (table.header || []).join(','),
      ...(table.rows || []).map(row => (row || []).map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${table.name || 'table'}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownload = () => {
    if (pdfUrl) {
      window.open(pdfUrl, '_blank');
    }
  };


  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center">
      <div className="bg-white dark:bg-slate-800 w-full h-full overflow-hidden flex flex-col rounded-lg">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center">
              <Table className="text-white" size={16} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Compare Statement</h2>
              <p className="text-xs text-slate-600 dark:text-slate-400">Review PDF and extracted data side by side</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="p-2 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col lg:flex-row w-full min-h-0 bg-slate-50 dark:bg-slate-900">
          {/* PDF Card */}
          <div className={`${isCollapsed ? 'w-0 hidden' : 'w-full lg:w-[30%]'} min-w-0 min-h-0 flex flex-col shadow-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 overflow-hidden flex-shrink-0 transition-all duration-300`}>
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
          </div>

          {/* Table Card */}
          <div className={`${isCollapsed ? 'w-full' : 'w-full lg:w-[70%]'} min-w-0 min-h-0 flex flex-col shadow-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 overflow-hidden flex-shrink-0 transition-all duration-300`}>
            <div className="flex items-center justify-between p-3 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                  <svg className="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0V4a1 1 0 011-1h16a1 1 0 011 1v16a1 1 0 01-1 1H4a1 1 0 01-1-1z" />
                  </svg>
                </div>
                <div className="flex items-center gap-4">
                  <h3 className="font-semibold text-slate-800 dark:text-slate-200">
                    {statement.edited_tables && statement.edited_tables.length > 0 ? 'Formatted Table(s)' : 'Extracted Table(s)'}
                  </h3>
                  {tables.length > 1 && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-600 dark:text-slate-400">Table:</span>
                      <select
                        value={currentTableIndex}
                        onChange={(e) => setCurrentTableIndex(Number(e.target.value))}
                        className="px-3 py-2 border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-900 dark:text-slate-100 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        {tables.map((table, index) => (
                          <option key={index} value={index}>
                            {table.name || `Table ${index + 1}`}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-600 dark:text-slate-400">
                      {currentTableIndex + 1} of {tables.length}
                    </span>
                    <span className="text-sm text-gray-600 dark:text-slate-400">
                      {currentTable?.rows?.length || 0} rows × {currentTable?.header?.length || 0} columns
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownload}
                  className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                  aria-label="Download PDF"
                >
                  <Download size={16} />
                </button>
                <button
                  onClick={() => downloadCSV(currentTable)}
                  className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                  aria-label="Download CSV"
                >
                  <FileText size={16} />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-auto">
              {tables.length === 0 ? (
                <div className="text-center py-16">
                  <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-xl flex items-center justify-center mx-auto mb-4">
                    <Table className="text-slate-400 dark:text-slate-500" size={32} />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">No extracted data found</h3>
                  <p className="text-slate-500 dark:text-slate-400 text-sm">This statement doesn&apos;t have any processed data yet.</p>
                </div>
              ) : (
                <div className="h-full flex flex-col">

                  {/* Table Display */}
                  {currentTable && (
                    <div className="flex-1 overflow-auto">
                      <div>

                        {/* Table */}
                        <div className="overflow-hidden shadow-sm bg-white dark:bg-slate-800">
                          <table className="min-w-full divide-y divide-gray-300 dark:divide-slate-600 company-table">
                            <thead className="bg-gray-50 dark:bg-slate-700 sticky top-0 z-20">
                              <tr className="border-b-2 border-gray-300 dark:border-slate-600">
                                {currentTable?.header?.map((header, index) => (
                                  <th
                                    key={index}
                                    className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-slate-300 border-r border-gray-200 dark:border-slate-600"
                                  >
                                    {header}
                                  </th>
                                )) || []}
                              </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-slate-800 divide-y divide-gray-200 dark:divide-slate-600">
                              {currentTable?.rows?.map((row, rowIndex) => (
                                <tr key={rowIndex} className="hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors">
                                  {row?.map((cell, cellIndex) => (
                                    <td key={cellIndex} className="px-4 py-3 text-sm text-gray-900 dark:text-slate-300 border-r border-gray-200 dark:border-slate-600">
                                      {cell}
                                    </td>
                                  )) || []}
                                </tr>
                              )) || []}
                            </tbody>
                          </table>
                        </div>

                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
