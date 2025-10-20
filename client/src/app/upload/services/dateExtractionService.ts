export interface ExtractedDate {
  date_value: string
  label: string
  confidence: number
  date_type: string
  context: string
  page_number: number
  bbox: number[]
}

export interface DateExtractionResponse {
  success: boolean
  filename: string
  company_id: string
  total_dates_found: number
  dates: ExtractedDate[]
  dates_by_type: Record<string, ExtractedDate[]>
  extraction_methods: string[]
  processing_time: number
  warnings: string[]
  errors: string[]
  metadata: {
    file_type: string
    extraction_timestamp: string
    service_version: string
  }
  error?: string
}

class DateExtractionService {
  private pendingRequests: Map<string, Promise<DateExtractionResponse>> = new Map()

  private getApiUrl(endpoint: string): string {
    // In development (localhost), use relative URL to leverage Next.js proxy
    // In production, use the full API URL
    const isDevelopment = typeof window !== 'undefined' && (
      window.location.hostname === 'localhost' || 
      window.location.hostname === '127.0.0.1'
    )
    
    if (isDevelopment) {
      // Use relative URL to avoid CORS issues in development
      return `/api${endpoint}`
    } else {
      // In production, use the full API URL
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || ''
      return `${apiUrl}${endpoint}`
    }
  }

  async extractDatesFromFile(file: File, companyId: string): Promise<DateExtractionResponse> {
    // Create a unique key for this request to prevent duplicate calls
    const requestKey = `${file.name}-${file.size}-${companyId}`
    
    // If there's already a pending request for this file, return that promise
    if (this.pendingRequests.has(requestKey)) {
      console.log('🔄 Date extraction already in progress for this file, returning existing promise')
      return this.pendingRequests.get(requestKey)!
    }

    // Create the request promise
    const requestPromise = this._performDateExtraction(file, companyId)
    
    // Store the promise to prevent duplicate requests
    this.pendingRequests.set(requestKey, requestPromise)
    
    try {
      const result = await requestPromise
      return result
    } finally {
      // Clean up the pending request
      this.pendingRequests.delete(requestKey)
    }
  }

  private async _performDateExtraction(file: File, companyId: string): Promise<DateExtractionResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('company_id', companyId)
    formData.append('max_pages', '1') // Only extract from first page

    try {
      const url = this.getApiUrl('/extract-dates/')
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'include', // Include credentials for authentication
      })


      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.error('❌ Date extraction failed:', errorData)
        
        // Return a successful response with no dates instead of throwing an error
        return {
          success: true,
          filename: file.name,
          company_id: companyId,
          total_dates_found: 0,
          dates: [],
          dates_by_type: {},
          extraction_methods: [],
          processing_time: 0,
          warnings: [],
          errors: [errorData.detail || `HTTP error! status: ${response.status}`],
          metadata: {
            file_type: file.type || 'unknown',
            extraction_timestamp: new Date().toISOString(),
            service_version: '1.0'
          }
        }
      }

      const data = await response.json()
      console.log('✅ Date extraction successful:', data)
      return data
    } catch (error) {
      console.error('❌ Date extraction failed:', error)
      
      // Return a successful response with no dates instead of throwing an error
      return {
        success: true,
        filename: file.name,
        company_id: companyId,
        total_dates_found: 0,
        dates: [],
        dates_by_type: {},
        extraction_methods: [],
        processing_time: 0,
        warnings: [],
        errors: [error instanceof Error ? error.message : 'Unknown error'],
        metadata: {
          file_type: file.type || 'unknown',
          extraction_timestamp: new Date().toISOString(),
          service_version: '1.0'
        }
      }
    }
  }

  async extractDatesFromBytes(file: File, companyId: string): Promise<DateExtractionResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('company_id', companyId)
    formData.append('max_pages', '1') // Only extract from first page

    try {
      const url = this.getApiUrl('/extract-dates-bytes/')
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'include', // Include credentials for authentication
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (error) {
      console.error('Date extraction from bytes failed:', error)
      throw error
    }
  }

  async getExtractionStatus(): Promise<any> {
    try {
      const url = this.getApiUrl('/date-extraction-status/')
      const response = await fetch(url, {
        credentials: 'include', // Include credentials for authentication
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Failed to get extraction status:', error)
      throw error
    }
  }
}

export const dateExtractionService = new DateExtractionService()
