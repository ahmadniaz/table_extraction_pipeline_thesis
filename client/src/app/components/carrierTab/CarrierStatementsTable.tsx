import React, { useState } from 'react';
import { Eye, LayoutList, Trash2, CheckCircle, XCircle, Clock, FileText, ExternalLink, ChevronLeft, ChevronRight, Table } from "lucide-react";
import { useRouter } from 'next/navigation';
import TableViewerModal from './TableViewerModal';

type Statement = {
  id: string;
  file_name: string;
  uploaded_at: string;
  status: string;
  rejection_reason?: string;
  selected_statement_date?: any;
  raw_data?: any;
  edited_tables?: any;
  final_data?: any;
};

type Props = {
  statements: Statement[];
  setStatements: React.Dispatch<React.SetStateAction<Statement[]>>;
  onPreview: (idx: number) => void;
  onCompare: (idx: number) => void;
  onDelete: (ids: string[]) => void;
  deleting?: boolean;
  canSelectFiles?: boolean;
  canDeleteFiles?: boolean;
};

export default function CarrierStatementsTable({ statements, setStatements, onPreview, onCompare, onDelete, deleting, canSelectFiles = true, canDeleteFiles = true }: Props) {
  const [selectedStatements, setSelectedStatements] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [tableViewerOpen, setTableViewerOpen] = useState(false);
  const [selectedStatementId, setSelectedStatementId] = useState<string>('');
  const [activeStatusTab, setActiveStatusTab] = useState<'all' | 'approved' | 'pending' | 'rejected'>('all');
  const itemsPerPage = 10;
  const router = useRouter();

  // Filter statements based on active status tab
  const filteredStatements = (statements || []).filter(statement => {
    if (activeStatusTab === 'all') return true;
    
    const status = statement.status.toLowerCase();
    switch (activeStatusTab) {
      case 'approved':
        return status === 'approved' || status === 'completed';
      case 'pending':
        return ['pending', 'extracted', 'success', 'processing'].includes(status);
      case 'rejected':
        return status === 'rejected';
      default:
        return true;
    }
  });

  const totalPages = Math.ceil(filteredStatements.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedStatements = filteredStatements.slice(startIndex, endIndex);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    setSelectedStatements(new Set()); // Clear selections when changing pages
    setSelectAll(false);
  };

  const handleStatusTabChange = (tab: 'all' | 'approved' | 'pending' | 'rejected') => {
    setActiveStatusTab(tab);
    setCurrentPage(1); // Reset to first page when changing tabs
    setSelectedStatements(new Set()); // Clear selections when changing tabs
    setSelectAll(false);
  };

  const handleCheckboxChange = (id: string) => {
   
    
    // Only block if user cannot select files, not based on deleting state
    if (!canSelectFiles) {
      console.log('Checkbox interaction blocked - user cannot select files');
      return;
    }
    
    setSelectedStatements(prevSelected => {
      const newSelectedStatements = new Set(prevSelected);
      if (newSelectedStatements.has(id)) {
        newSelectedStatements.delete(id);
        console.log('Removed statement from selection:', id);
      } else {
        newSelectedStatements.add(id);
        console.log('Added statement to selection:', id);
      }
      console.log('Updated selectedStatements:', Array.from(newSelectedStatements));
      return newSelectedStatements;
    });
  };

  const handleDelete = () => {
    if (selectedStatements.size > 0) {
      const idsToDelete = Array.from(selectedStatements);
      onDelete(idsToDelete);
      setSelectedStatements(new Set());
      setSelectAll(false);
    }
  };

  const handleSelectAllChange = () => {
    const newSelectedStatements = new Set<string>();
    if (!selectAll) {
      paginatedStatements.forEach(statement => newSelectedStatements.add(statement.id));
    }
    setSelectedStatements(newSelectedStatements);
    setSelectAll(!selectAll);
  };

  const handleViewFormattedTables = (statementId: string) => {
    setSelectedStatementId(statementId);
    setTableViewerOpen(true);
  };

  const normalizeFileName = (fileName: string) => {
    // Extract just the filename from the full path
    const parts = fileName.split('/');
    return parts[parts.length - 1];
  };

  const formatStatementDate = (selectedStatementDate: any) => {
    if (!selectedStatementDate) return '—';
    
    try {
      // Handle different date formats that might be stored
      const dateStr = selectedStatementDate.date || selectedStatementDate.date_value || selectedStatementDate;
      
      if (typeof dateStr === 'string') {
        // Handle different date formats
        let date: Date;
        
        // Try parsing as MM/DD/YYYY format first (common in US)
        if (dateStr.includes('/')) {
          const parts = dateStr.split('/');
          if (parts.length === 3) {
            // MM/DD/YYYY format
            date = new Date(parseInt(parts[2]), parseInt(parts[0]) - 1, parseInt(parts[1]));
          } else {
            date = new Date(dateStr);
          }
        } else {
          // Try standard Date parsing for ISO format
          date = new Date(dateStr);
        }
        
        if (!isNaN(date.getTime())) {
          return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
          });
        }
      }
      
      return dateStr || '—';
    } catch (error) {
      console.error('Error formatting statement date:', error, selectedStatementDate);
      return '—';
    }
  };

  const getStatusInfo = (status: string) => {
    switch (status.toLowerCase()) {
      case 'approved':
      case 'completed':
        return {
          label: 'Approved',
          color: 'success',
          icon: CheckCircle,
          bgColor: 'bg-success/10',
          textColor: 'text-success',
          borderColor: 'border-success/20'
        };
      case 'rejected':
        return {
          label: 'Rejected',
          color: 'destructive',
          icon: XCircle,
          bgColor: 'bg-destructive/10',
          textColor: 'text-destructive',
          borderColor: 'border-destructive/20'
        };
      case 'pending':
      case 'extracted':
      case 'success':
      default:
        return {
          label: 'Pending',
          color: 'warning',
          icon: Clock,
          bgColor: 'bg-warning/10',
          textColor: 'text-warning',
          borderColor: 'border-warning/20'
        };
    }
  };

  return (
    <div className="overflow-hidden relative">
      {deleting && (
        <div className="absolute inset-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm flex items-center justify-center z-10 rounded-xl">
          <div className="flex items-center space-x-3">
            <div className="w-6 h-6 border-2 border-slate-200 dark:border-slate-600 border-t-red-500 rounded-full animate-spin"></div>
            <span className="text-slate-700 dark:text-slate-300 font-medium">Deleting statements...</span>
          </div>
        </div>
      )}
      
      {/* Enhanced Delete Button */}
      {selectedStatements.size > 0 && canDeleteFiles && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Trash2 className="text-red-600 dark:text-red-400" size={20} />
              <span className="text-red-700 dark:text-red-300 font-medium">
                {selectedStatements.size} statement{selectedStatements.size !== 1 ? 's' : ''} selected for deletion
              </span>
            </div>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg font-medium shadow-sm hover:bg-red-600 transition-all duration-200 disabled:opacity-50"
            >
              <Trash2 size={16} />
              {deleting ? 'Deleting...' : 'Delete Selected'}
            </button>
          </div>
        </div>
      )}

      {/* Read-only mode indicator */}
      {!canSelectFiles && (
        <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-600 rounded-xl">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 bg-amber-100 dark:bg-amber-800/60 rounded-full flex items-center justify-center">
              <span className="text-amber-600 dark:text-amber-200 text-xs">🔒</span>
            </div>
            <span className="text-amber-700 dark:text-amber-200 font-medium">
              Read-only mode - You can view data but cannot make changes
            </span>
          </div>
        </div>
      )}

      {/* Status Tabs */}
      <div className="mb-6">
        <div className="flex items-center gap-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-1">
          <button
            onClick={() => handleStatusTabChange('all')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              activeStatusTab === 'all'
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <span>All</span>
            <span className="text-xs bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 px-2 py-1 rounded-full">
              {statements?.length || 0}
            </span>
          </button>
          <button
            onClick={() => handleStatusTabChange('approved')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              activeStatusTab === 'approved'
                ? 'bg-green-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <CheckCircle size={16} />
            <span>Approved</span>
            <span className="text-xs bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 px-2 py-1 rounded-full">
              {(statements || []).filter(s => s.status.toLowerCase() === 'approved' || s.status.toLowerCase() === 'completed').length}
            </span>
          </button>
          <button
            onClick={() => handleStatusTabChange('pending')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              activeStatusTab === 'pending'
                ? 'bg-orange-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <Clock size={16} />
            <span>Pending</span>
            <span className="text-xs bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 px-2 py-1 rounded-full">
              {(statements || []).filter(s => ['pending', 'extracted', 'success', 'processing'].includes(s.status.toLowerCase())).length}
            </span>
          </button>
          <button
            onClick={() => handleStatusTabChange('rejected')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              activeStatusTab === 'rejected'
                ? 'bg-red-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <XCircle size={16} />
            <span>Rejected</span>
            <span className="text-xs bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 px-2 py-1 rounded-full">
              {(statements || []).filter(s => s.status.toLowerCase() === 'rejected').length}
            </span>
          </button>
        </div>
      </div>

      {/* Enhanced Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden w-full">
        <table className="w-full border-collapse company-table">
          <thead className="bg-slate-50 dark:bg-slate-700/50">
            <tr>
              <th className="px-6 py-4 w-12">
                {canSelectFiles ? (
                  <input
                    type="checkbox"
                    checked={selectAll}
                    onChange={(e) => {
                      console.log('Select All checkbox onChange triggered');
                      e.stopPropagation();
                      handleSelectAllChange();
                    }}
                    onClick={(e) => {
                      console.log('Select All checkbox onClick triggered', 'current selectAll state:', selectAll);
                      e.stopPropagation();
                      // Since onChange might not be working, handle the toggle directly in onClick
                      handleSelectAllChange();
                    }}
                    className="w-4 h-4 text-blue-500 border-slate-300 dark:border-slate-600 rounded focus:ring-blue-500 cursor-pointer"
                    style={{ pointerEvents: 'auto', zIndex: 10 }}
                  />
                ) : (
                  <div className="w-4 h-4 border border-slate-300 dark:border-slate-600 rounded bg-slate-100 dark:bg-slate-700" title="Selection disabled"></div>
                )}
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                <div className="flex items-center gap-2">
                  <FileText size={16} className="text-slate-500 dark:text-slate-400" />
                  Statement
                </div>
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Uploaded On</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Statement Date</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Rejection Reason</th>
              <th className="px-6 py-4 text-center text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedStatements.map((statement, idx) => {
              const statusInfo = getStatusInfo(statement.status);
              const StatusIcon = statusInfo.icon;
              
              return (
                <tr 
                  key={statement.id} 
                  className="hover:bg-slate-50/50 dark:hover:bg-slate-700/50 transition-colors duration-200 animate-fade-in"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <td className="px-6 py-4">
                    {canSelectFiles ? (
                      <input
                        type="checkbox"
                        checked={selectedStatements.has(statement.id)}
                        onChange={(e) => {
                          console.log('Checkbox onChange triggered for:', statement.id, 'checked:', e.target.checked);
                          e.stopPropagation();
                          handleCheckboxChange(statement.id);
                        }}
                        onClick={(e) => {
                          console.log('Checkbox onClick triggered for:', statement.id, 'current checked state:', selectedStatements.has(statement.id));
                          e.stopPropagation();
                          // Since onChange might not be working, handle the toggle directly in onClick
                          handleCheckboxChange(statement.id);
                        }}
                        className="w-4 h-4 text-blue-500 border-slate-300 dark:border-slate-600 rounded focus:ring-blue-500 cursor-pointer"
                        style={{ pointerEvents: 'auto', zIndex: 10 }}
                      />
                    ) : (
                      <div className="w-4 h-4 border border-slate-300 dark:border-slate-600 rounded bg-slate-100 dark:bg-slate-700" title="Selection disabled"></div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                        <FileText size={16} className="text-blue-600 dark:text-blue-400" />
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{normalizeFileName(statement.file_name)}</div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">ID: {statement.id.slice(0, 8)}...</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-slate-900 dark:text-slate-100">
                      {new Date(statement.uploaded_at).toLocaleDateString()}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {new Date(statement.uploaded_at).toLocaleTimeString()}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-slate-900 dark:text-slate-100">
                      {formatStatementDate(statement.selected_statement_date)}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium border ${statusInfo.bgColor} ${statusInfo.textColor} ${statusInfo.borderColor}`}>
                      <StatusIcon size={14} />
                      {statusInfo.label}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="max-w-xs">
                      {statement.rejection_reason ? (
                        <div className="text-sm text-slate-600 dark:text-slate-300 bg-red-50 dark:bg-red-950/40 p-2 rounded-lg border border-red-200 dark:border-red-800">
                          {statement.rejection_reason}
                        </div>
                      ) : (
                        <span className="text-slate-400 dark:text-slate-500">—</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-center gap-2">
                      {/* Show eye icon only for approved/rejected statements */}
                      {(statement.status === "Approved" || statement.status === "completed" || statement.status === "Rejected" || statement.status === "rejected") && (
                        <button
                          title="View mapped table"
                          className="p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                          onClick={() => onPreview(startIndex + idx)}
                        >
                          <Eye size={16} />
                        </button>
                      )}
                      
                      <button
                        title="Compare mapped & extracted"
                        className="p-2 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/30 rounded-lg transition-colors"
                        onClick={() => onCompare(startIndex + idx)}
                      >
                        <LayoutList size={16} />
                      </button>

                      {/* Formatted table viewing button */}
                      <button
                        title="View formatted tables"
                        className="p-2 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-lg transition-colors"
                        onClick={() => handleViewFormattedTables(statement.id)}
                      >
                        <Table size={16} />
                      </button>
                      
                      {(statement.status === "Pending" || statement.status === "pending" || statement.status === "extracted" || statement.status === "success") && (
                        <button
                          onClick={() => router.push(`/upload?resume=${statement.id}`)}
                          className="inline-flex items-center gap-1 px-3 py-2 bg-blue-500 text-white rounded-lg font-medium shadow-sm hover:bg-blue-600 transition-all duration-200 text-sm"
                          title="Complete Review"
                        >
                          <ExternalLink size={14} />
                          Review
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-700">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="inline-flex items-center px-4 py-2 border border-slate-300 dark:border-slate-600 text-sm font-medium rounded-lg text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="ml-3 inline-flex items-center px-4 py-2 border border-slate-300 dark:border-slate-600 text-sm font-medium rounded-lg text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="inline-flex items-center px-3 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm font-medium rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <span className="text-sm text-slate-700 dark:text-slate-300 font-medium">
                  Page <span className="font-semibold">{currentPage}</span> of{' '}
                  <span className="font-semibold">{totalPages}</span>
                </span>
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="inline-flex items-center px-3 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm font-medium rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {filteredStatements.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-slate-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <FileText className="h-8 w-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-700 mb-2">
              {activeStatusTab === 'all' ? 'No statements found' : `No ${activeStatusTab} statements found`}
            </h3>
            <p className="text-slate-500 text-sm">
              {activeStatusTab === 'all' 
                ? 'Upload statements to see them listed here'
                : `Try selecting a different status tab to view other statements`
              }
            </p>
          </div>
        )}
      </div>

      {/* Table Viewer Modal */}
      <TableViewerModal
        isOpen={tableViewerOpen}
        onClose={() => setTableViewerOpen(false)}
        statementId={selectedStatementId}
        tableType="formatted"
        title="Formatted Tables"
        statement={(statements || []).find(s => s.id === selectedStatementId)}
      />
    </div>
  );
}
