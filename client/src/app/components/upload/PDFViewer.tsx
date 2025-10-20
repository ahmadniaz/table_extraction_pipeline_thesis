'use client'

import { useState, useEffect, useMemo } from 'react'
import { Worker, Viewer, SpecialZoomLevel } from '@react-pdf-viewer/core'
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout'

// Import styles
import '@react-pdf-viewer/core/lib/styles/index.css'
import '@react-pdf-viewer/default-layout/lib/styles/index.css'

interface PDFViewerProps {
  fileUrl: string
  isCollapsed: boolean
  onToggleCollapse: () => void
}

export default function PDFViewer({ fileUrl, isCollapsed, onToggleCollapse }: PDFViewerProps) {
  const [isClient, setIsClient] = useState(false)
  
  // Use proxy endpoint to avoid CORS issues with direct GCS URLs
  const proxiedUrl = useMemo(() => {
    if (!fileUrl) return ''
    
    // If it's a GCS URL, proxy it through our backend
    if (fileUrl.includes('storage.googleapis.com')) {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      return `${apiUrl}/api/pdf-proxy?url=${encodeURIComponent(fileUrl)}`
    }
    
    // Otherwise use the URL as-is
    return fileUrl
  }, [fileUrl])
  
  // Initialize the default layout plugin
  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    sidebarTabs: (defaultTabs) => [defaultTabs[0]], // Only show thumbnails tab
    toolbarPlugin: {
      fullScreenPlugin: {
        onEnterFullScreen: (zoom) => {
          zoom(SpecialZoomLevel.PageFit)
        },
      },
    },
  })

  // ✅ CRITICAL: Ensure client-side only rendering
  useEffect(() => {
    setIsClient(true)
  }, [])

  // Don't render PDF until client-side
  if (!isClient) {
    return (
      <div className="w-full h-full bg-gray-50 dark:bg-slate-900 border-r border-gray-200 dark:border-slate-700 flex items-center justify-center flex-shrink-0">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600 dark:text-slate-400">Initializing PDF viewer...</p>
        </div>
      </div>
    )
  }

  if (isCollapsed) {
    return (
      <div className="w-12 h-full bg-gray-100 dark:bg-slate-800 border-r border-gray-200 dark:border-slate-700 relative z-20">
        <div className="px-1 py-3">
          <button
            onClick={onToggleCollapse}
            className="transform rotate-90 bg-blue-600 dark:bg-blue-700 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors shadow-lg"
            aria-label="Show PDF Preview"
          >
            Open
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full h-full bg-gray-50 dark:bg-slate-900 border-r border-gray-200 dark:border-slate-700 flex flex-col flex-shrink-0">
      {/* Header with controls */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Document Preview</h3>
        
        <div className="flex items-center space-x-2">
          {fileUrl && (
            <button
              onClick={() => window.open(fileUrl, '_blank')}
              className="px-3 py-1 bg-blue-600 dark:bg-blue-700 text-white rounded text-sm hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors"
              title="Open in New Tab"
            >
              Open
            </button>
          )}
          
          <button
            onClick={onToggleCollapse}
            className="px-3 py-1 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-slate-300 rounded text-sm hover:bg-gray-300 dark:hover:bg-slate-600 transition-colors"
            title="Hide PDF Preview"
          >
            Hide
          </button>
        </div>
      </div>

      {/* PDF Content */}
      <div className="flex-1 overflow-hidden bg-gray-100 w-full h-full">
        {!fileUrl ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500">
              <svg className="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="font-medium">No PDF file available</p>
              <p className="text-sm text-gray-400 mt-2">Upload a document to preview</p>
            </div>
          </div>
        ) : (
          <Worker workerUrl={`https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js`}>
            <div className="h-full w-full">
              <Viewer
                fileUrl={proxiedUrl}
                plugins={[defaultLayoutPluginInstance]}
                defaultScale={SpecialZoomLevel.PageFit}
                theme={{
                  theme: 'light',
                }}
                renderError={(error) => (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center text-red-600 max-w-md p-8">
                      <div className="text-red-500 mb-4">
                        <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <p className="text-red-600 mb-4 font-semibold">Failed to load PDF</p>
                      <p className="text-gray-600 text-sm mb-6">{error.message}</p>
                      {fileUrl && (
                        <button
                          onClick={() => window.open(fileUrl, '_blank')}
                          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                        >
                          Open in New Tab
                        </button>
                      )}
                    </div>
                  </div>
                )}
              />
            </div>
          </Worker>
        )}
      </div>
    </div>
  )
}

