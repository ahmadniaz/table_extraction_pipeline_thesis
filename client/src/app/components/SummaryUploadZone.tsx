'use client'

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  FileText,
  FileSpreadsheet,
  X,
  CheckCircle,
  AlertCircle,
  Shield,
  Building2,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import SummaryProgressLoader from './upload/SummaryProgressLoader ';
import { useProgressWebSocket } from '../hooks/useProgressWebSocket';
import toast from 'react-hot-toast';
import axios from 'axios';

interface CarrierUploadZoneProps {
  onParsed: (result: {
    tables: any[],
    upload_id?: string,
    file_name: string,
    file: File,
    quality_summary?: any,
    extraction_config?: any,
    format_learning?: any,
    gcs_url?: string,
    gcs_key?: string,
    extracted_carrier?: string,
    extracted_date?: string,
    document_metadata?: any,
    ai_intelligence?: any,
    carrier_id?: string,
    company_id?: string
  }) => void;
  selectedStatementDate?: any;
  extractionMethod?: string;
  onExtractionMethodChange?: (method: string) => void;
  onContinue?: () => void;
}

export default function CarrierUploadZone({
  onParsed,
  selectedStatementDate,
  extractionMethod,
  onExtractionMethodChange,
  onContinue
}: CarrierUploadZoneProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState('');
  const [stageProgress, setStageProgress] = useState(0);
  const [stageMessage, setStageMessage] = useState('');
  const [estimatedTime, setEstimatedTime] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [localPdfUrl, setLocalPdfUrl] = useState<string | null>(null);
  const [extractedPages, setExtractedPages] = useState<File | null>(null);
  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [uploadDate, setUploadDate] = useState<string | null>(null);
  const [completionDate, setCompletionDate] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);
  const [n8nResponse, setN8nResponse] = useState<any>(null);
  const [isN8nLoading, setIsN8nLoading] = useState(false);
  
  // 🚫 PAUSE POINT: Store extraction results for manual continuation
  // TODO: Remove these states when reverting to automatic flow
  const [extractionResults, setExtractionResults] = useState<any>(null);
  const [isExtractionComplete, setIsExtractionComplete] = useState(false);

  // Memoize callbacks to prevent unnecessary re-renders
  const handleExtractionComplete = useCallback((results: any) => {
    // 🚫 PAUSE POINT: Don't automatically proceed - store results and wait for Continue button
    // TODO: Remove this pause - uncomment the original automatic flow below
    setExtractionResults(results);
    setIsExtractionComplete(true);
    // Keep isUploading true so the progress loader stays visible
    
    // ORIGINAL AUTOMATIC FLOW (commented out for manual control):
    // setIsUploading(false);
    // if (results && results.success) {
    //   onParsed({
    //     tables: results.tables || [],
    //     upload_id: results.upload_id,
    //     file_name: results.file_name || uploadedFile?.name || '',
    //     file: uploadedFile!,
    //     quality_summary: results.quality_summary,
    //     extraction_config: results.extraction_config,
    //     gcs_url: results.gcs_url,
    //     gcs_key: results.gcs_key,
    //     extracted_carrier: results.extracted_carrier,
    //     extracted_date: results.extracted_date,
    //     document_metadata: results.document_metadata,
    //     ai_intelligence: results.ai_intelligence
    //   });
    // }
  }, []);
  
  const handleWebSocketError = useCallback((errorMsg: string) => {
    console.error('WebSocket error:', errorMsg);
    setError(errorMsg);
    setIsUploading(false);
  }, []);

  // Extract first 3 pages from PDF and send to Claude API
  const extractAndSendPages = useCallback(async (file: File): Promise<void> => {
    console.log('🚀 Starting extractAndSendPages with file:', file.name);
    setIsN8nLoading(true);
    try {
      // Create a new PDF with only first 3 pages using PDF-lib
      console.log('📚 Importing pdf-lib...');
      const pdfLib = await import('pdf-lib');
      const { PDFDocument } = pdfLib;
      
      console.log('📄 Loading PDF...');
      const existingPdfBytes = await file.arrayBuffer();
      const pdfDoc = await PDFDocument.load(existingPdfBytes);
      const pageCount = pdfDoc.getPageCount();
      console.log('📊 PDF page count:', pageCount);
      setTotalPages(pageCount);
      
      // Only extract if PDF has more than 3 pages
      if (pageCount > 3) {
        console.log('✂️ Extracting first 3 pages...');
        const newPdf = await PDFDocument.create();
        const pages = await newPdf.copyPages(pdfDoc, [0, 1, 2]); // First 3 pages (0-indexed)
        pages.forEach((page) => newPdf.addPage(page));
        
        const pdfBytes = await newPdf.save();
        const extractedFile = new File([new Uint8Array(pdfBytes)], `extracted_${file.name}`, { type: 'application/pdf' });
        setExtractedPages(extractedFile);
        
        // Send to Claude API
        console.log('📤 Sending extracted pages to Claude API...');
        const formData = new FormData();
        formData.append('file', extractedFile);
        
        const response = await axios.post('/api/extract-summarize-data-via-claude/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          withCredentials: true,
        });
        
        console.log('📡 Claude response status:', response.status);
        if (response.status === 200) {
          const responseData = response.data;
          console.log('✅ Claude response data:', responseData);
          setN8nResponse(responseData);
          setCompletionDate(new Date().toLocaleString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZoneName: 'short'
          }));
          console.log('✅ First 3 pages sent to Claude API successfully', responseData);
        } else {
          console.error('❌ Failed to send pages to Claude API:', response.statusText);
        }
        setIsN8nLoading(false);
      } else {
        console.log('📄 PDF has 3 or fewer pages, no extraction needed');
        // Send original file if 3 pages or less
        console.log('📤 Sending original PDF to Claude API...');
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await axios.post('/api/extract-summarize-data-via-claude/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          withCredentials: true,
        });
        
        console.log('📡 Claude response status:', response.status);
        if (response.status === 200) {
          const responseData = response.data;
          console.log('✅ Claude response data:', responseData);
          setN8nResponse(responseData);
          setCompletionDate(new Date().toLocaleString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZoneName: 'short'
          }));
          console.log('✅ Original PDF sent to Claude API successfully', responseData);
        } else {
          console.error('❌ Failed to send original PDF to Claude API:', response.statusText);
        }
        setIsN8nLoading(false);
      }
    } catch (error) {
      console.error('❌ Error extracting PDF pages:', error);
      setIsN8nLoading(false);
    }
  }, []);

  // Resend file to Claude API
  const resendToClaude = useCallback(async () => {
    if (!uploadedFile) return;

    setIsResending(true);
    setIsN8nLoading(true);
    try {
      let fileToSend = uploadedFile;
      
      // If we have extracted pages, use those; otherwise use original
      if (extractedPages) {
        fileToSend = extractedPages;
      }
      
      const formData = new FormData();
      formData.append('file', fileToSend);
      
      const response = await axios.post('/api/extract-summarize-data-via-claude/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        withCredentials: true,
      });
      
      if (response.status === 200) {
        const responseData = response.data;
        setN8nResponse(responseData);
        setCompletionDate(new Date().toLocaleString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          timeZoneName: 'short'
        }));
        toast.success('File resent to Claude API successfully!');
        console.log('✅ File resent to Claude API successfully', responseData);
      } else {
        toast.error('Failed to resend file to Claude API');
        console.error('❌ Failed to resend file to Claude API:', response.statusText);
      }
    } catch (error) {
      toast.error('Error resending file to Claude API');
      console.error('❌ Error resending file to Claude API:', error);
    } finally {
      setIsResending(false);
      setIsN8nLoading(false);
    }
  }, [uploadedFile, extractedPages]);

  // Handle Continue button click
  const handleContinue = useCallback(() => {
    // 🚫 PAUSE POINT: Manual continuation - this function can be removed when reverting to automatic
    // TODO: Remove this function and the manual Continue button when reverting to automatic flow
    if (extractionResults && extractionResults.success) {
      // Now proceed with the results
      setIsUploading(false);
      onParsed({
        tables: extractionResults.tables || [],
        upload_id: extractionResults.upload_id,
        file_name: extractionResults.file_name || uploadedFile?.name || '',
        file: uploadedFile!,
        quality_summary: extractionResults.quality_summary,
        extraction_config: extractionResults.extraction_config,
        gcs_url: extractionResults.gcs_url,
        gcs_key: extractionResults.gcs_key,
        extracted_carrier: extractionResults.extracted_carrier,
        extracted_date: extractionResults.extracted_date,
        document_metadata: extractionResults.document_metadata,
        ai_intelligence: extractionResults.ai_intelligence,
        carrier_id: extractionResults.carrier_id,  // ✅ CRITICAL: Pass carrier_id for AI field mapping
        company_id: extractionResults.company_id   // ✅ CRITICAL: Pass company_id as fallback
      });
    }
  }, [extractionResults, uploadedFile, onParsed]);
  
  // Use new WebSocket hook for premium progress tracking
  const { progress: wsProgress } = useProgressWebSocket({
    uploadId: uploadId || undefined,
    autoConnect: true,  // ✅ Auto-connect when uploadId changes
    onExtractionComplete: handleExtractionComplete,
    onError: handleWebSocketError
  });

  // Handle upload click
  const handleUploadClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (isUploading) return;
    
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.xlsx,.xls,.xlsm,.xlsb';
    input.multiple = false;
    
    input.onchange = (event) => {
      const files = (event.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        handleFileUpload([files[0]]);
      }
    };
    
    input.click();
  }, [isUploading]);

  // Handle select files button click specifically
  const handleSelectFilesClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (isUploading) return;
    
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.xlsx,.xls,.xlsm,.xlsb';
    input.multiple = false;
    
    input.onchange = (event) => {
      const files = (event.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        handleFileUpload([files[0]]);
      }
    };
    
    input.click();
  }, [isUploading]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      handleFileUpload(acceptedFiles);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.ms-excel.sheet.macroEnabled.12': ['.xlsm'],
      'application/vnd.ms-excel.sheet.binary.macroEnabled.12': ['.xlsb']
    },
    multiple: false,
    disabled: isUploading,
    noClick: true, // We handle clicks manually
    noKeyboard: true
  });


  // Commission-specific error handling
  const getCommissionSpecificErrorMessage = (error: string, fileName: string) => {
    const fileExt = fileName.split('.').pop()?.toLowerCase();
    
    if (error.includes('No tables found')) {
      return `No commission tables detected in ${fileName}. Please ensure your document contains commission statement tables with clear headers and data rows.`;
    }
    if (error.includes('Unsupported format')) {
      return `The file format .${fileExt} is not supported. Please upload PDF or Excel files containing commission statements from supported carriers.`;
    }
    if (error.includes('file too large')) {
      return `File size exceeds 50MB limit. Please compress your commission statement or split large files.`;
    }
    if (error.includes('corrupted') || error.includes('invalid')) {
      return `The file appears to be corrupted or invalid. Please try re-saving your commission statement and uploading again.`;
    }
    if (error.includes('carrier not supported')) {
      return `This carrier format is not yet supported. Currently supported: Aetna, Blue Cross Blue Shield, Cigna, Humana, United Healthcare.`;
    }
    
    return `Processing error: ${error}. Please check your commission statement format and try again.`;
  };

  const handleFileUpload = async (files: File[]) => {
    const file = files[0];
    if (!file) return;

    setUploadedFile(file);
    setIsUploading(true);
    setError(null);
    setUploadProgress(0);
    setCurrentStage('Initializing');
    setStageProgress(0);
    
    // Set upload date
    const uploadDateStr = new Date().toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short'
    });
    setUploadDate(uploadDateStr);
    
    // Generate local PDF URL for preview
    const localUrl = URL.createObjectURL(file);
    setLocalPdfUrl(localUrl);
    
    try {
      const newUploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      console.log('🆔 Generated uploadId:', newUploadId);
      setUploadId(newUploadId);

      // Small delay to allow WebSocket to connect before API call
      console.log('⏱️ Waiting 500ms for WebSocket to connect...');
      await new Promise(resolve => setTimeout(resolve, 500));
      console.log('✅ Proceeding with file upload');

      // Start summarization in parallel (if it's a PDF) - will extract first 3 pages
      if (file.type === 'application/pdf') {
        console.log('📝 Starting summarization in parallel (first 3 pages)...');
        extractAndSendPages(file); // Don't await - run in parallel, extracts first 3 pages
      }

      // Start table extraction in parallel (full file)
      const formData = new FormData();
      formData.append('file', file); // Full file for table extraction
      formData.append('extraction_method', 'smart');  // Use 'smart' to default to Claude AI
      formData.append('upload_id', newUploadId);
      
      if (selectedStatementDate) {
        formData.append('statement_date', selectedStatementDate);
      }

      console.log('📤 Starting table extraction API call with uploadId:', newUploadId);
      const response = await axios.post('/api/extract-tables-smart/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        withCredentials: true,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          }
        },
      });

      // WebSocket will handle the progress updates automatically via useProgressWebSocket hook
      console.log('Table extraction started, WebSocket will handle progress updates');

    } catch (error: any) {
      setIsUploading(false);
      
      // Handle 409 conflict (duplicate file) specifically
      if (error.response?.status === 409) {
        const conflictData = error.response?.data;
        if (conflictData?.status === 'duplicate_detected') {
          const duplicateInfo = conflictData.duplicate_info;
          const uploadDate = duplicateInfo?.existing_upload_date_formatted || 'a previous date';
          
          // Set user-friendly error message
          const errorMsg = `This file was already uploaded on ${uploadDate}. Please upload a different file or check your existing uploads.`;
          setError(errorMsg);
          
          // Show toast notification
          toast.error('Duplicate File Detected', {
            duration: 5000,
            icon: '⚠️',
          });
          
          return;
        }
      }
      
      const errorMessage = error.response?.data?.error || error.message || 'Upload failed';
      setError(getCommissionSpecificErrorMessage(errorMessage, file.name));
      toast.error('Upload failed. Please try again.');
    }
  };

  const handleCancel = async () => {
    // Cancel the extraction on the backend if we have an upload ID
    if (uploadId) {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/cancel-extraction/${uploadId}`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (response.ok) {
          toast.success('Extraction cancelled successfully');
        } else {
          console.warn('Failed to cancel extraction on backend:', response.statusText);
        }
      } catch (error) {
        console.error('Error cancelling extraction:', error);
        // Don't show error toast for cancellation failures as user is already cancelling
      }
    }
    
    setIsUploading(false);
    setUploadProgress(0);
    setCurrentStage('');
    setStageProgress(0);
    setError(null);
    setUploadedFile(null);
    setExtractionResults(null);
    setIsExtractionComplete(false);
    setExtractedPages(null);
    setTotalPages(null);
    setUploadDate(null);
    setCompletionDate(null);
    setIsResending(false);
    setN8nResponse(null);
    
    // Cleanup local PDF URL
    if (localPdfUrl) {
      URL.revokeObjectURL(localPdfUrl);
      setLocalPdfUrl(null);
    }
  };

  const handleRetry = () => {
    if (uploadedFile) {
      handleFileUpload([uploadedFile]);
    }
  };

  const handleReset = () => {
    setUploadedFile(null);
    setError(null);
    setUploadProgress(0);
    setCurrentStage('');
    setStageProgress(0);
    setExtractionResults(null);
    setIsExtractionComplete(false);
    setExtractedPages(null);
    setTotalPages(null);
    setUploadDate(null);
    setCompletionDate(null);
    setIsResending(false);
    setN8nResponse(null);
    
    // Cleanup local PDF URL
    if (localPdfUrl) {
      URL.revokeObjectURL(localPdfUrl);
      setLocalPdfUrl(null);
    }
  };

  // PREMIUM: Show premium loader with step-by-step progress when processing
  // 🚫 PAUSE POINT: Added isExtractionComplete to keep loader visible after completion
  // TODO: Remove || isExtractionComplete when reverting to automatic flow
  if (isUploading || isExtractionComplete) {
    return (
      <div className="w-full h-full">
        <SummaryProgressLoader
          currentStep={wsProgress.currentStep}
          progress={wsProgress.percentage || stageProgress}
          estimatedTime={wsProgress.estimatedTimeRemaining || estimatedTime}
          isVisible={true}
          pdfUrl={localPdfUrl}
          onContinue={handleContinue}
          summaryContent={(() => {
            // Don't show summary during loading or if no response
            if (isN8nLoading || !n8nResponse) {
              return null;
            }
            
            // Extract summary content from Claude response
            if (n8nResponse.summary) {
              return n8nResponse.summary;
            }
            
            if (n8nResponse.content) {
              // Look for markdown code blocks anywhere in the content
              const markdownMatch = n8nResponse.content.match(/```markdown\n([\s\S]*?)\n```/);
              if (markdownMatch) {
                return markdownMatch[1]; // Return the content inside the markdown block
              }
              
              // If no markdown block found, return the full content
              return n8nResponse.content;
            }
            
            if (Array.isArray(n8nResponse) && n8nResponse[0]?.choices?.[0]?.message?.content) {
              return n8nResponse[0].choices[0].message.content;
            }
            
            return null;
          })()}
          metadataContent={(() => {
            return `
## Document Metadata

### File Information
- **Original File**: ${uploadedFile?.name || 'Unknown'}
- **File Size**: ${uploadedFile ? (uploadedFile.size / 1024 / 1024).toFixed(2) + ' MB' : 'Unknown'}
- **File Type**: ${uploadedFile?.type || 'Unknown'}
- **Upload Date**: ${uploadDate || 'Unknown'}
- **Processing Status**: ${isN8nLoading ? '🔄 In Progress' : '✅ Completed'}

### PDF Processing Details
${extractedPages ? `
- **Pages Extracted**: First 3 pages (${uploadedFile?.name} had more than 3 pages)
- **Extracted File**: ${extractedPages.name}
- **Extraction Method**: PDF-lib automatic extraction
- **Processing Type**: Partial document analysis
` : `
- **Pages**: Using original file (${uploadedFile?.name} - ${totalPages || 'Unknown'} pages)
- **Processing**: Full document analysis
- **Processing Type**: Complete document analysis
`}

### AI Analysis Details
- **Analysis Date**: ${completionDate || uploadDate || 'Unknown'}
- **Processing Time**: Real-time analysis
- **Data Quality**: High confidence extraction

---
*Analysis ${isN8nLoading ? 'started' : 'completed'} at ${isN8nLoading ? uploadDate : completionDate || 'Unknown'}*`;
          })()}
        />
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-[calc(100vh-300px)]">
      {/* Clean, Minimal Upload Zone */}
      <div
        {...getRootProps()}
        onClick={handleUploadClick}
        className={`
          relative border-2 border-dashed rounded-2xl p-8 md:p-12 text-center transition-all duration-300 h-full flex flex-col justify-center
          ${isDragActive
            ? 'border-blue-400 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/20 scale-[1.02] cursor-pointer' 
            : 'border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50 hover:border-blue-300 dark:hover:border-blue-500 hover:bg-blue-25 dark:hover:bg-blue-900/10 cursor-pointer'
          }
        `}
      >
        <input {...getInputProps()} />
        
        <AnimatePresence mode="wait">
          {(
            <motion.div
              key="default"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="space-y-8"
            >
              {/* Header */}
              <div>
                <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-slate-800 via-blue-600 to-purple-600 dark:from-slate-100 dark:via-blue-400 dark:to-purple-400 bg-clip-text text-transparent mb-4">
                  AI-Powered Commission Processing
                </h1>
                <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
                  Upload your commission statements and let AI automatically detect carriers, extract dates, and process tables
                </p>
              </div>

              {/* Upload Section */}
              <div className="space-y-6">
                <div className="w-20 h-20 mx-auto bg-gradient-to-r from-green-500 to-blue-600 rounded-full flex items-center justify-center">
                  <FileSpreadsheet className="w-10 h-10 text-white" />
                </div>
                
                <div>
                  <h3 className="text-xl font-bold text-slate-800 dark:text-slate-200 mb-2">
                    Ready to Upload
                  </h3>
                  <p className="text-slate-600 dark:text-slate-400">
                    Drag & drop your files here or click to browse
                  </p>
                </div>

                <motion.button
                  type="button"
                  onClick={handleSelectFilesClick}
                  className="px-8 py-3 bg-gradient-to-r from-green-500 to-blue-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-200 cursor-pointer"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className="flex items-center gap-2">
                    <Upload className="w-5 h-5" />
                    Select Files
                  </div>
                </motion.button>
              </div>

              {/* Features Grid */}
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-slate-500 dark:text-slate-400">
                  <div className="flex items-center justify-center gap-2">
                    <Shield className="w-4 h-4" />
                    <span>Secure Processing</span>
                  </div>
                  <div className="flex items-center justify-center gap-2">
                    <FileText className="w-4 h-4" />
                    <span>PDF & Excel Supported</span>
                  </div>
                  <div className="flex items-center justify-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    <span>AI Auto-Detection</span>
                  </div>
                </div>
              </div>

              {/* File Format Info */}
              <div className="text-xs text-slate-400 dark:text-slate-500 space-y-1">
                <p><strong>Supported formats:</strong> PDF, XLSX, XLS, XLSM, XLSB</p>
                <p><strong>Max file size:</strong> 50MB per file</p>
                <p><strong>Auto-detects:</strong> Aetna, BCBS, Cigna, Humana, UHC</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl"
        >
          <div className="flex items-start gap-4">
            <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-1" />
            <div className="flex-1">
              <p className="text-red-800 dark:text-red-200 font-semibold mb-2 text-lg">Upload Error</p>
              <p className="text-red-700 dark:text-red-300 mb-4">{error}</p>
              <button
                onClick={handleRetry}
                className="px-4 py-2 bg-red-100 dark:bg-red-800/30 text-red-700 dark:text-red-200 rounded-lg text-sm hover:bg-red-200 dark:hover:bg-red-800/50 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Resend to n8n Button */}
      {uploadedFile && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 flex justify-center"
        >
          <button
            onClick={resendToClaude}
            disabled={isResending}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg font-semibold transition-colors duration-200 flex items-center gap-2"
          >
            {isResending ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Resending...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Resend to Claude
              </>
            )}
          </button>
        </motion.div>
      )}
    </div>
  );
}
