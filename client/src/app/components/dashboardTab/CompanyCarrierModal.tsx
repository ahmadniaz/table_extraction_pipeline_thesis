import React from 'react';
import { X, Building2, Truck, ArrowLeft } from 'lucide-react';

interface CarrierInfo {
  carrier_name: string;
  commission_earned: number;
  invoice_total: number;
  statement_count: number;
  statement_year?: number;
}

interface CompanyCarrierModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBack?: () => void;
  companyName: string;
  carriers: CarrierInfo[];
}

const CompanyCarrierModal: React.FC<CompanyCarrierModalProps> = ({
  isOpen,
  onClose,
  onBack,
  companyName,
  carriers
}) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const totalCommission = carriers.reduce((sum, c) => sum + c.commission_earned, 0);
  const totalInvoice = carriers.reduce((sum, c) => sum + c.invoice_total, 0);
  const totalStatements = carriers.reduce((sum, c) => sum + c.statement_count, 0);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {onBack && (
                <button
                  onClick={onBack}
                  className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                  title="Back to companies list"
                >
                  <ArrowLeft size={20} className="text-slate-600 dark:text-slate-400" />
                </button>
              )}
              <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                <Building2 className="text-blue-600 dark:text-blue-400" size={24} />
                Company Carriers
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X size={20} className="text-slate-500 dark:text-slate-400" />
            </button>
          </div>
          
          {/* Company Info */}
          <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
            <h3 className="font-semibold text-slate-800 dark:text-slate-200 text-lg mb-2">
              {companyName}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-slate-600 dark:text-slate-400">Total Carriers:</span>
                <span className="ml-2 font-semibold text-slate-800 dark:text-slate-200">
                  {carriers.length}
                </span>
              </div>
              <div>
                <span className="text-slate-600 dark:text-slate-400">Total Commission:</span>
                <span className="ml-2 font-semibold text-emerald-600 dark:text-emerald-400">
                  {formatCurrency(totalCommission)}
                </span>
              </div>
              <div>
                <span className="text-slate-600 dark:text-slate-400">Total Statements:</span>
                <span className="ml-2 font-semibold text-slate-800 dark:text-slate-200">
                  {totalStatements}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Carriers List */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-200px)]">
          {carriers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-500 dark:text-slate-400">
              <Truck className="text-slate-300 dark:text-slate-600 mb-4" size={48} />
              <p className="text-lg font-medium">No carriers found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {carriers.map((carrier, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg border border-slate-200 dark:border-slate-600"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-orange-600 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                      <Truck size={16} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                        {carrier.carrier_name || 'Unknown Carrier'}
                      </h4>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {carrier.statement_count} statements
                        {carrier.statement_year && ` • Year: ${carrier.statement_year}`}
                      </p>
                    </div>
                  </div>
                  
                  <div className="text-right ml-4">
                    <p className="font-bold text-emerald-600 dark:text-emerald-400">
                      {formatCurrency(carrier.commission_earned)}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Invoice: {formatCurrency(carrier.invoice_total)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/30">
          <div className="flex items-center justify-between text-sm text-slate-600 dark:text-slate-400">
            <span>Showing all {carriers.length} carriers for this company</span>
            <div className="flex items-center gap-4">
              <span>Total Commission: 
                <span className="font-bold text-emerald-600 dark:text-emerald-400 ml-1">
                  {formatCurrency(totalCommission)}
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CompanyCarrierModal;

