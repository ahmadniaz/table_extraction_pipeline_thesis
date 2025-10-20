'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Clock, FileText, Play, Trash2, AlertCircle, CheckCircle, Calendar } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { useSubmission } from '@/context/SubmissionContext'

interface PendingFile {
  id: string
  company_id: string
  company_name: string
  file_name: string
  uploaded_at: string
  current_step: string
  last_updated: string
  progress_summary: string
}

export default function PendingFilesPage() {
  const router = useRouter()
  const { triggerDashboardRefresh } = useSubmission();
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAllPendingFiles()
  }, [])

  const fetchAllPendingFiles = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Get all companies first
      const companiesResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/companies/`)
      if (!companiesResponse.ok) {
        throw new Error('Failed to fetch companies')
      }
      
      const companies = await companiesResponse.json()
      
      // Fetch pending files for all companies
      const allPendingFiles: PendingFile[] = []
      
      for (const company of companies) {
        try {
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/pending/files/${company.id}`)
          if (response.ok) {
            const data = await response.json()
            if (data.success && data.pending_files) {
              // Add company name to each pending file
              const filesWithCompany = data.pending_files.map((file: any) => ({
                ...file,
                company_name: company.name
              }))
              allPendingFiles.push(...filesWithCompany)
            }
          }
        } catch (err) {
          console.error(`Error fetching pending files for company ${company.name}:`, err)
        }
      }
      
      setPendingFiles(allPendingFiles)
    } catch (err) {
      console.error('Error fetching pending files:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch pending files')
      toast.error('Failed to load pending files')
    } finally {
      setLoading(false)
    }
  }

  const handleResumeFile = async (fileId: string) => {
    try {
      // Navigate to upload page with the file ID
      router.push(`/upload?resume=${fileId}`)
    } catch (error) {
      console.error('Error resuming file:', error)
      toast.error('Failed to resume file')
    }
  }

  const handleReviewFile = async (fileId: string) => {
    try {
      // Navigate to upload page with the file ID for review
      router.push(`/upload?resume=${fileId}&step=dashboard`)
    } catch (error) {
      console.error('Error reviewing file:', error)
      toast.error('Failed to review file')
    }
  }

  const handleDeleteFile = async (fileId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/pending/delete/${fileId}`, {
        method: 'DELETE',
        credentials: 'include'  // Include authentication cookies
      })
      
      if (!response.ok) {
        throw new Error('Failed to delete pending file')
      }
      
      const data = await response.json()
      
      if (data.success) {
        setPendingFiles(prev => prev.filter(file => file.id !== fileId))
        toast.success('Pending file deleted successfully')
        // Trigger global dashboard refresh after successful deletion
        triggerDashboardRefresh();
      } else {
        throw new Error(data.message || 'Failed to delete pending file')
      }
    } catch (err) {
      console.error('Error deleting pending file:', err)
      toast.error('Failed to delete pending file')
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    // Convert to local timezone for display
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Karachi' // Use Pakistan timezone
    })
  }

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    // Both dates are in UTC, so the difference calculation is correct
    const diffInMs = now.getTime() - date.getTime()
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60))
    const diffInDays = Math.floor(diffInHours / 24)
    
    if (diffInDays > 0) {
      return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`
    } else if (diffInHours > 0) {
      return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`
    } else {
      const diffInMinutes = Math.floor(diffInMs / (1000 * 60))
      return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`
    }
  }

  const stepIcons = {
    upload: <FileText className="w-4 h-4" />,
    table_editor: <FileText className="w-4 h-4" />,
    field_mapper: <FileText className="w-4 h-4" />,
    dashboard: <FileText className="w-4 h-4" />,
    completed: <CheckCircle className="w-4 h-4" />
  }

  const stepColors = {
    upload: 'bg-blue-100 text-blue-800',
    table_editor: 'bg-yellow-100 text-yellow-800',
    field_mapper: 'bg-purple-100 text-purple-800',
    dashboard: 'bg-green-100 text-green-800',
    completed: 'bg-gray-100 text-gray-800'
  }

  const stepLabels = {
    upload: 'Upload',
    table_editor: 'Table Editor',
    field_mapper: 'Field Mapper',
    dashboard: 'Dashboard',
    completed: 'Completed'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-white rounded-full transition-colors"
          >
            <ArrowLeft size={24} className="text-gray-600" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Pending Files</h1>
            <p className="text-gray-600">Resume or manage your incomplete uploads</p>
          </div>
        </div>

        {/* Content */}
        <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Clock className="w-5 h-5 text-orange-600 mr-2" />
                <h2 className="text-xl font-semibold text-gray-800">All Pending Files</h2>
                <span className="ml-2 bg-orange-100 text-orange-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                  {pendingFiles.length}
                </span>
              </div>
              <button
                onClick={fetchAllPendingFiles}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                Refresh
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-gray-600">Loading pending files...</span>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-12 text-red-600">
              <AlertCircle className="w-6 h-6 mr-2" />
              <span>{error}</span>
            </div>
          ) : pendingFiles.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-600 mb-2">No Pending Files</h3>
              <p className="text-gray-500">All your files have been processed or you haven&apos;t started any uploads yet.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {pendingFiles.map((file) => (
                <div key={file.id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center mb-2">
                        <FileText className="w-5 h-5 text-gray-400 mr-2 flex-shrink-0" />
                        <h3 className="text-sm font-medium text-gray-900 truncate">
                          {file.file_name}
                        </h3>
                      </div>
                      
                      <div className="flex items-center mb-3">
                        <span className="text-sm font-medium text-gray-700 mr-3">
                          {file.company_name}
                        </span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${stepColors[file.current_step as keyof typeof stepColors]}`}>
                          {stepIcons[file.current_step as keyof typeof stepIcons]}
                          <span className="ml-1">{stepLabels[file.current_step as keyof typeof stepLabels]}</span>
                        </span>
                        <span className="ml-3 text-sm text-gray-500">
                          {file.progress_summary}
                        </span>
                      </div>
                      
                      <div className="flex items-center text-xs text-gray-500 space-x-4">
                        <div className="flex items-center">
                          <Calendar className="w-3 h-3 mr-1" />
                          <span>Uploaded {formatDate(file.uploaded_at)}</span>
                        </div>
                        <div className="flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          <span>Updated {getTimeAgo(file.last_updated)}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2 ml-4">
                      {file.current_step === 'dashboard' ? (
                        <button
                          onClick={() => handleReviewFile(file.id)}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
                        >
                          <CheckCircle className="w-4 h-4 mr-1" />
                          Review
                        </button>
                      ) : (
                        <button
                          onClick={() => handleResumeFile(file.id)}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                        >
                          <Play className="w-4 h-4 mr-1" />
                          Resume
                        </button>
                      )}
                      
                      <button
                        onClick={() => handleDeleteFile(file.id)}
                        className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
} 