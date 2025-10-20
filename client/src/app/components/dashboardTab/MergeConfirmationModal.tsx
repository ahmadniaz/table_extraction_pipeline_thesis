'use client'
import React from 'react';
import { AlertTriangle, Merge, X, DollarSign, Building2 } from 'lucide-react';

interface CommissionData {
  id: string;
  client_name: string;
  invoice_total: number;
  commission_earned: number;
  statement_count: number;
  last_updated?: string;
}

interface MergeConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  existingRecord: CommissionData;
  newData: {
    client_name: string;
    invoice_total: number;
    commission_earned: number;
  };
  onConfirmMerge: () => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}

export default function MergeConfirmationModal({
  isOpen,
  onClose,
  existingRecord,
  newData,
  onConfirmMerge,
  onCancel,
  loading = false
}: MergeConfirmationModalProps) {
  if (!isOpen) return null;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const calculateMergedTotals = () => {
    const mergedInvoice = existingRecord.invoice_total + newData.invoice_total;
    const mergedCommission = existingRecord.commission_earned + newData.commission_earned;
    const mergedStatements = existingRecord.statement_count + 1; // +1 for the new record being merged
    
    return {
      invoice: mergedInvoice,
      commission: mergedCommission,
      statements: mergedStatements
    };
  };

  const mergedTotals = calculateMergedTotals();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-r from-amber-500 to-orange-600 rounded-xl flex items-center justify-center shadow-lg">
              <AlertTriangle className="text-white" size={24} />
            </div>
            <h2 className="text-2xl font-bold text-slate-800">Company Name Already Exists</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-700 text-2xl font-bold p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            ×
          </button>
        </div>

        <div className="space-y-6">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
            <p className="text-amber-800 font-semibold">
              A company with the name <span className="font-bold">&ldquo;{newData.client_name}&rdquo;</span> already exists for this carrier.
            </p>
            <p className="text-amber-700 text-sm mt-3">
              Would you like to merge this data with the existing record?
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Existing Record */}
            <div className="bg-slate-50 rounded-xl p-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
                  <Building2 className="text-slate-600" size={18} />
                </div>
                <h3 className="font-semibold text-slate-800">Existing Record</h3>
              </div>
              
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-slate-600 font-medium">Company Name</p>
                  <p className="font-semibold text-slate-800">{existingRecord.client_name}</p>
                </div>
                
                <div>
                  <p className="text-sm text-slate-600 font-medium">Invoice Total</p>
                  <p className="font-semibold text-slate-800">{formatCurrency(existingRecord.invoice_total)}</p>
                </div>
                
                <div>
                  <p className="text-sm text-slate-600 font-medium">Commission Earned</p>
                  <p className="font-semibold text-slate-800">{formatCurrency(existingRecord.commission_earned)}</p>
                </div>
                
                <div>
                  <p className="text-sm text-slate-600 font-medium">Statement Count</p>
                  <p className="font-semibold text-slate-800">{existingRecord.statement_count}</p>
                </div>
              </div>
            </div>

            {/* New Data */}
            <div className="bg-blue-50 rounded-xl p-6 border border-blue-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                  <DollarSign className="text-blue-600" size={18} />
                </div>
                <h3 className="font-semibold text-blue-800">New Data</h3>
              </div>
              
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-blue-600 font-medium">Company Name</p>
                  <p className="font-semibold text-blue-800">{newData.client_name}</p>
                </div>
                
                <div>
                  <p className="text-sm text-blue-600 font-medium">Invoice Total</p>
                  <p className="font-semibold text-blue-800">{formatCurrency(newData.invoice_total)}</p>
                </div>
                
                <div>
                  <p className="text-sm text-blue-600 font-medium">Commission Earned</p>
                  <p className="font-semibold text-blue-800">{formatCurrency(newData.commission_earned)}</p>
                </div>
                
                <div>
                  <p className="text-sm text-blue-600 font-medium">Statement Count</p>
                  <p className="font-semibold text-blue-800">1</p>
                </div>
              </div>
            </div>
          </div>

          {/* Merged Result Preview */}
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                <Merge className="text-emerald-600" size={18} />
              </div>
              <h3 className="font-semibold text-emerald-800">Merged Result (Preview)</h3>
            </div>
            
            <div className="grid grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-emerald-600 font-medium">Total Invoice</p>
                <p className="font-bold text-emerald-800 text-lg">{formatCurrency(mergedTotals.invoice)}</p>
              </div>
              
              <div>
                <p className="text-sm text-emerald-600 font-medium">Total Commission</p>
                <p className="font-bold text-emerald-800 text-lg">{formatCurrency(mergedTotals.commission)}</p>
              </div>
              
              <div>
                <p className="text-sm text-emerald-600 font-medium">Total Statements</p>
                <p className="font-bold text-emerald-800 text-lg">{mergedTotals.statements}</p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4 pt-4">
            <button
              onClick={onCancel}
              disabled={loading}
              className="flex-1 px-6 py-3 bg-slate-200 text-slate-700 rounded-xl font-semibold hover:bg-slate-300 transition-all duration-200 disabled:opacity-50"
            >
              Cancel - Use Different Name
            </button>
            
            <button
              onClick={onConfirmMerge}
              disabled={loading}
              className="flex-1 px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl font-semibold hover:from-emerald-600 hover:to-teal-700 transition-all duration-200 disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Merging...
                </>
              ) : (
                <>
                  <Merge size={18} />
                  Merge Records
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
