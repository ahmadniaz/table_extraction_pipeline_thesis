'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Upload, Shield, Sparkles, Building2, Calendar } from 'lucide-react';
import BeautifulUploadZone from './BeautifulUploadZone';
import { useAuth } from '@/context/AuthContext';
import toast from 'react-hot-toast';

export default function UploadPageContent() {
  const router = useRouter();
  const { user } = useAuth();
  const [extractedCarrier, setExtractedCarrier] = useState<string | null>(null);
  const [extractedDate, setExtractedDate] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleUploadResult = (result: {
    tables: any[];
    upload_id?: string;
    file_name: string;
    file: File;
    quality_summary?: any;
    extraction_config?: any;
    format_learning?: any;
    gcs_url?: string;
    gcs_key?: string;
    extracted_carrier?: string;
    extracted_date?: string;
    document_metadata?: any;
    carrier_id?: string;
    company_id?: string;
  }) => {
    // Handle successful upload
    toast.success('Document uploaded and processed successfully!');
    
    // Store extracted information
    if (result.extracted_carrier) {
      setExtractedCarrier(result.extracted_carrier);
    }
    if (result.extracted_date) {
      setExtractedDate(result.extracted_date);
    }
    
    // Navigate to carriers tab with the extracted carrier pre-selected
    if (result.extracted_carrier) {
      // Encode the carrier name to handle special characters in URLs
      const encodedCarrier = encodeURIComponent(result.extracted_carrier);
      router.push(`/?tab=carriers&carrier=${encodedCarrier}`);
    } else {
      // Fallback to carriers tab if no carrier was extracted
      router.push('/?tab=carriers');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 shadow-sm border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16">
            <button
              onClick={() => router.back()}
              className="flex items-center gap-2 px-3 py-2 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
            <div className="flex items-center gap-3 ml-4">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <Upload className="h-4 w-4 text-white" />
              </div>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">Upload Statements</h1>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg border border-slate-200 dark:border-slate-700 p-8">
          <div className="text-center">
            <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
              <Sparkles className="h-10 w-10 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-3">AI-Powered Commission Processing</h2>
            <p className="text-slate-600 dark:text-slate-400 mb-8 text-lg">
              Simply upload your statements - our AI will automatically detect the carrier and extract all data
            </p>
            
            {/* AI Extraction Status */}
            {isProcessing && (
              <div className="mb-8 p-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
                <div className="flex items-center justify-center gap-3">
                  <div className="w-6 h-6 border-2 border-blue-500 dark:border-blue-400 border-t-transparent rounded-full animate-spin" />
                  <p className="text-blue-800 dark:text-blue-200 font-medium">
                    AI is analyzing your document...
                  </p>
                </div>
              </div>
            )}

            {/* Extracted Information Display */}
            {(extractedCarrier || extractedDate) && (
              <div className="mb-8 p-6 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl">
                <h3 className="text-lg font-semibold text-emerald-800 dark:text-emerald-200 mb-4">AI Detection Results</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {extractedCarrier && (
                    <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-800 rounded-lg border border-emerald-200 dark:border-emerald-800">
                      <Building2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                      <div>
                        <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">Carrier</p>
                        <p className="text-emerald-800 dark:text-emerald-200 font-semibold">{extractedCarrier}</p>
                      </div>
                    </div>
                  )}
                  {extractedDate && (
                    <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-800 rounded-lg border border-emerald-200 dark:border-emerald-800">
                      <Calendar className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                      <div>
                        <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">Statement Date</p>
                        <p className="text-emerald-800 dark:text-emerald-200 font-semibold">{extractedDate}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {/* Functional Upload Zone */}
            <BeautifulUploadZone
              onParsed={handleUploadResult}
              disabled={false}
              companyId={user?.company_id || ''}
            />

            {/* Security Notice */}
            <div className="mt-8 p-6 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl">
              <div className="flex items-center justify-center gap-3">
                <div className="w-8 h-8 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg flex items-center justify-center">
                  <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                </div>
                <p className="text-sm text-emerald-800 dark:text-emerald-200 font-medium">
                  Your files are securely processed and stored with enterprise-grade security
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
