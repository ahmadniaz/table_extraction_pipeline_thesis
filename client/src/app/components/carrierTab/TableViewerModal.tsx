import React, { useState, useEffect, useCallback } from 'react';
import { X, Database, Table, Download, Eye, FileText } from 'lucide-react';

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

interface TableViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  statementId: string;
  tableType: 'formatted';
  title: string;
  statement?: any; // Pass the statement data directly
}

export default function TableViewerModal({ 
  isOpen, 
  onClose, 
  statementId, 
  tableType, 
  title,
  statement 
}: TableViewerModalProps) {
  const [tables, setTables] = useState<TableData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentTableIndex, setCurrentTableIndex] = useState(0);

  const loadTablesFromStatement = useCallback(() => {
    setLoading(true);
    setError(null);
    
    try {
      // Use existing data from the statement instead of making API calls
      // For formatted tables, use edited_tables if available, otherwise fall back to raw_data
      const tableData = statement.edited_tables || statement.raw_data || [];
      
      if (Array.isArray(tableData) && tableData.length > 0) {
        setTables(tableData);
        setCurrentTableIndex(0);
      } else {
        setTables([]);
        setError('No table data available for this statement');
      }
    } catch (err) {
      setError('Error loading table data');
      console.error('Error loading tables:', err);
    } finally {
      setLoading(false);
    }
  }, [statement]);

  useEffect(() => {
    if (isOpen && statement) {
      loadTablesFromStatement();
    }
  }, [isOpen, statement, loadTablesFromStatement]);

  const downloadCSV = (table: TableData) => {
    const csvContent = [
      (table.header || []).join(','),
      ...(table.rows || []).map(row => (row || []).map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${table.name || 'table'}_${tableType}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const currentTable = tables[currentTableIndex];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-7xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
              <Table className="text-white" size={20} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">{title}</h2>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Formatted and processed data
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)] bg-slate-50 dark:bg-slate-900">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-slate-200 dark:border-slate-700 border-t-emerald-500 rounded-full animate-spin"></div>
              <span className="ml-3 text-slate-600 dark:text-slate-400 font-medium">Loading tables...</span>
            </div>
          ) : error ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-xl flex items-center justify-center mx-auto mb-4">
                <FileText className="text-red-600 dark:text-red-400" size={32} />
              </div>
              <h3 className="text-lg font-semibold text-red-700 dark:text-red-300 mb-2">Error Loading Tables</h3>
              <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
            </div>
          ) : tables.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Table className="text-slate-400 dark:text-slate-500" size={32} />
              </div>
              <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">No tables found</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm">This statement doesn&apos;t have any processed tables yet.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Table Navigation */}
              {tables.length > 1 && (
                <div className="flex items-center justify-between bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center gap-4">
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
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600 dark:text-slate-400">
                      {currentTableIndex + 1} of {tables.length}
                    </span>
                  </div>
                </div>
              )}

              {/* Table Display */}
              {currentTable && (
                <div className="space-y-4">
                  {/* Table Header */}
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-200">
                        {currentTable.name || `Table ${currentTableIndex + 1}`}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-slate-400">
                        {currentTable.rows?.length || 0} rows × {currentTable.header?.length || 0} columns
                      </p>
                    </div>
                    <button
                      onClick={() => downloadCSV(currentTable)}
                      className="flex items-center gap-2 px-4 py-2 bg-slate-600 dark:bg-slate-700 text-white rounded-lg hover:bg-slate-700 dark:hover:bg-slate-600 transition-colors"
                    >
                      <Download size={16} />
                      Download CSV
                    </button>
                  </div>

                  {/* Table */}
                  <div className="overflow-x-auto border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800">
                    <table className="w-full company-table">
                      <thead className="bg-gray-50 dark:bg-slate-700">
                        <tr>
                          {currentTable.header?.map((header, index) => (
                            <th
                              key={index}
                              className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-slate-300 border-b border-gray-200 dark:border-slate-600"
                            >
                              {header}
                            </th>
                          )) || []}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 dark:divide-slate-600">
                        {currentTable.rows?.map((row, rowIndex) => (
                          <tr key={rowIndex} className="hover:bg-gray-50 dark:hover:bg-slate-700">
                            {row?.map((cell, cellIndex) => (
                              <td
                                key={cellIndex}
                                className="px-4 py-3 text-sm text-gray-900 dark:text-slate-300 whitespace-nowrap"
                              >
                                {cell}
                              </td>
                            )) || []}
                          </tr>
                        )) || []}
                      </tbody>
                    </table>
                  </div>

                  {/* Table Metadata */}
                  {currentTable.metadata && (
                    <div className="bg-white dark:bg-slate-800 p-4 rounded-lg border border-slate-200 dark:border-slate-700">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">Table Information</h4>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        {currentTable.extractor && (
                          <div>
                            <span className="text-gray-600 dark:text-slate-400">Extractor:</span>
                            <span className="ml-2 text-gray-900 dark:text-slate-300">{currentTable.extractor}</span>
                          </div>
                        )}
                        {currentTable.metadata.extraction_method && (
                          <div>
                            <span className="text-gray-600 dark:text-slate-400">Method:</span>
                            <span className="ml-2 text-gray-900 dark:text-slate-300">{currentTable.metadata.extraction_method}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600 dark:text-slate-400">
              {tables.length} table{tables.length !== 1 ? 's' : ''} available
            </p>
            <button
              onClick={onClose}
              className="px-6 py-2 bg-slate-600 dark:bg-slate-700 text-white rounded-lg hover:bg-slate-700 dark:hover:bg-slate-600 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
