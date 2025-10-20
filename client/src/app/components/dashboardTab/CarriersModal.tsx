import React, { useState } from 'react';
import { X, Database, FileText, ChevronLeft, ChevronRight } from 'lucide-react';

interface Carrier {
  id: string;
  name: string;
  statement_count: number;
}

interface CarriersModalProps {
  isOpen: boolean;
  onClose: () => void;
  carriers: Carrier[];
  loading?: boolean;
}

export default function CarriersModal({ isOpen, onClose, carriers, loading = false }: CarriersModalProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  
  const totalPages = Math.ceil(carriers.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedCarriers = carriers.slice(startIndex, endIndex);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
              <Database className="text-white" size={24} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-800">All Carriers</h2>
              <p className="text-sm text-slate-600">{carriers.length} total carriers</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-180px)]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-slate-200 border-t-blue-500 rounded-full animate-spin"></div>
              <span className="ml-3 text-slate-600 font-medium">Loading carriers...</span>
            </div>
          ) : carriers.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 bg-slate-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Database className="text-slate-400" size={32} />
              </div>
              <h3 className="text-lg font-semibold text-slate-700 mb-2">No carriers found</h3>
              <p className="text-slate-500 text-sm">No carriers have been added yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {paginatedCarriers.map((carrier) => (
                <div
                  key={carrier.id}
                  className="flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors border border-slate-200"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
                      <span className="text-white font-semibold text-sm">
                        {carrier.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-800">{carrier.name}</h3>
                      <p className="text-sm text-slate-500">ID: {carrier.id.slice(0, 8)}...</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                      <FileText className="text-emerald-600" size={16} />
                    </div>
                    <span className="font-semibold text-slate-800">
                      {carrier.statement_count} statement{carrier.statement_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pagination */}
        {carriers.length > itemsPerPage && (
          <div className="px-6 py-4 border-t border-slate-200 bg-slate-50">
            <div className="flex items-center justify-between">
              <div className="text-sm text-slate-600 font-medium">
                Showing {startIndex + 1} to {Math.min(endIndex, carriers.length)} of {carriers.length} carriers
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="flex items-center gap-1 px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft size={16} />
                  Previous
                </button>
                
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }
                    
                    return (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                          currentPage === pageNum
                            ? 'bg-blue-600 text-white'
                            : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>
                
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="flex items-center gap-1 px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="p-6 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-600 font-medium">
              Total: {carriers.length} carrier{carriers.length !== 1 ? 's' : ''}
            </p>
            <button
              onClick={onClose}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
} 