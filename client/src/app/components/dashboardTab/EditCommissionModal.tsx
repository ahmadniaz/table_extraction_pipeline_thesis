'use client'
import React, { useState, useEffect } from 'react';
import { X, Save, DollarSign, Building2, TrendingUp } from 'lucide-react';

interface CommissionData {
  id: string;
  carrier_name?: string;
  client_name: string;
  invoice_total: number;
  commission_earned: number;
  statement_count: number;
  last_updated?: string;
  created_at?: string;
}

interface EditCommissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: CommissionData | null;
  onSave: (updatedData: Partial<CommissionData>) => Promise<void>;
  loading?: boolean;
}

export default function EditCommissionModal({ 
  isOpen, 
  onClose, 
  data, 
  onSave, 
  loading = false 
}: EditCommissionModalProps) {
  const [formData, setFormData] = useState({
    client_name: '',
    invoice_total: '',
    commission_earned: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (data) {
      setFormData({
        client_name: data.client_name || '',
        invoice_total: data.invoice_total?.toString() || '',
        commission_earned: data.commission_earned?.toString() || ''
      });
      setErrors({});
    }
  }, [data]);

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.client_name.trim()) {
      newErrors.client_name = 'Company name is required';
    }

    const invoiceTotal = parseFloat(formData.invoice_total.replace(/[$,]/g, ''));
    if (isNaN(invoiceTotal) || invoiceTotal < 0) {
      newErrors.invoice_total = 'Please enter a valid invoice amount';
    }

    const commissionEarned = parseFloat(formData.commission_earned.replace(/[$,]/g, ''));
    if (isNaN(commissionEarned) || commissionEarned < 0) {
      newErrors.commission_earned = 'Please enter a valid commission amount';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) return;

    try {
      const invoiceTotal = parseFloat(formData.invoice_total.replace(/[$,]/g, ''));
      const commissionEarned = parseFloat(formData.commission_earned.replace(/[$,]/g, ''));

      await onSave({
        id: data?.id || '',
        client_name: formData.client_name.trim(),
        invoice_total: invoiceTotal,
        commission_earned: commissionEarned
      });

      onClose();
    } catch (error) {
      console.error('Error saving commission data:', error);
    }
  };

  const formatCurrencyInput = (value: string) => {
    // Remove all non-numeric characters except decimal point
    const numericValue = value.replace(/[^0-9.]/g, '');
    
    // Ensure only one decimal point
    const parts = numericValue.split('.');
    if (parts.length > 2) {
      return parts[0] + '.' + parts.slice(1).join('');
    }
    
    return numericValue;
  };

  const formatCurrencyDisplay = (value: string) => {
    if (!value) return '';
    const numericValue = parseFloat(value);
    if (isNaN(numericValue)) return value;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(numericValue);
  };

  if (!isOpen || !data) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center shadow-lg">
              <TrendingUp className="text-white" size={20} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-800">Edit Commission Data</h2>
              <p className="text-sm text-slate-600">Update company and commission information</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <div className="p-6 space-y-6">
          {/* Company Name */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              <Building2 className="inline mr-2" size={16} />
              Company Name
            </label>
            <input
              type="text"
              value={formData.client_name}
              onChange={(e) => handleInputChange('client_name', e.target.value)}
              className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 ${
                errors.client_name ? 'border-red-300' : 'border-slate-200'
              }`}
              placeholder="Enter company name"
            />
            {errors.client_name && (
              <p className="mt-1 text-sm text-red-600">{errors.client_name}</p>
            )}
          </div>

          {/* Invoice Total */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              <DollarSign className="inline mr-2" size={16} />
              Invoice Total
            </label>
            <input
              type="text"
              value={formData.invoice_total}
              onChange={(e) => handleInputChange('invoice_total', formatCurrencyInput(e.target.value))}
              className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 ${
                errors.invoice_total ? 'border-red-300' : 'border-slate-200'
              }`}
              placeholder="0.00"
            />
            {formData.invoice_total && (
              <p className="mt-1 text-sm text-slate-500">
                {formatCurrencyDisplay(formData.invoice_total)}
              </p>
            )}
            {errors.invoice_total && (
              <p className="mt-1 text-sm text-red-600">{errors.invoice_total}</p>
            )}
          </div>

          {/* Commission Earned */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              <TrendingUp className="inline mr-2" size={16} />
              Commission Earned
            </label>
            <input
              type="text"
              value={formData.commission_earned}
              onChange={(e) => handleInputChange('commission_earned', formatCurrencyInput(e.target.value))}
              className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 ${
                errors.commission_earned ? 'border-red-300' : 'border-slate-200'
              }`}
              placeholder="0.00"
            />
            {formData.commission_earned && (
              <p className="mt-1 text-sm text-slate-500">
                {formatCurrencyDisplay(formData.commission_earned)}
              </p>
            )}
            {errors.commission_earned && (
              <p className="mt-1 text-sm text-red-600">{errors.commission_earned}</p>
            )}
          </div>

          {/* Read-only Info */}
          <div className="bg-slate-50 rounded-xl p-4 space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-600 font-medium">Statements:</span>
              <span className="font-semibold text-slate-800">{data.statement_count}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-600 font-medium">Last Updated:</span>
              <span className="font-semibold text-slate-800">
                {data.last_updated ? new Date(data.last_updated).toLocaleDateString() : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-4 p-6 border-t border-slate-200">
          <button
            onClick={onClose}
            className="flex-1 px-6 py-3 text-slate-700 bg-slate-200 hover:bg-slate-300 rounded-xl font-semibold transition-all duration-200"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="flex-1 px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white rounded-xl font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Saving...
              </>
            ) : (
              <>
                <Save size={16} />
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
