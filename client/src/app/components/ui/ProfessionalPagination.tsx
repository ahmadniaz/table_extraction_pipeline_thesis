'use client'
import { ChevronLeft, ChevronRight, MoreHorizontal } from 'lucide-react'
import clsx from 'clsx'

interface ProfessionalPaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
  className?: string
}

export default function ProfessionalPagination({
  currentPage,
  totalPages,
  onPageChange,
  className = ''
}: ProfessionalPaginationProps) {
  if (totalPages <= 1) return null

  const getVisiblePages = () => {
    const delta = 2 // Number of pages to show on each side of current page
    const range = []
    const rangeWithDots = []

    // Calculate the range of pages to show
    for (let i = Math.max(2, currentPage - delta); i <= Math.min(totalPages - 1, currentPage + delta); i++) {
      range.push(i)
    }

    // Always show first page
    if (currentPage - delta > 2) {
      rangeWithDots.push(1, '...')
    } else {
      rangeWithDots.push(1)
    }

    // Add the range
    rangeWithDots.push(...range)

    // Always show last page
    if (currentPage + delta < totalPages - 1) {
      rangeWithDots.push('...', totalPages)
    } else if (totalPages > 1) {
      rangeWithDots.push(totalPages)
    }

    return rangeWithDots
  }

  const visiblePages = getVisiblePages()

  return (
    <div className={clsx('flex items-center justify-center space-x-1', className)}>
      {/* Previous Button */}
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        className={clsx(
          'flex items-center px-3 py-2 text-sm font-medium rounded-lg border transition-colors',
          currentPage <= 1
            ? 'text-gray-400 dark:text-slate-500 bg-gray-50 dark:bg-slate-700 border-gray-200 dark:border-slate-600 cursor-not-allowed'
            : 'text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700 hover:border-gray-400 dark:hover:border-slate-500'
        )}
      >
        <ChevronLeft size={16} className="mr-1" />
        Previous
      </button>

      {/* Page Numbers */}
      <div className="flex items-center space-x-1">
        {visiblePages.map((page, index) => {
          if (page === '...') {
            return (
              <span
                key={`dots-${index}`}
                className="px-3 py-2 text-sm font-medium text-gray-500 dark:text-slate-400"
              >
                <MoreHorizontal size={16} />
              </span>
            )
          }

          const pageNumber = page as number
          const isCurrentPage = pageNumber === currentPage

          return (
            <button
              key={pageNumber}
              onClick={() => onPageChange(pageNumber)}
              className={clsx(
                'px-3 py-2 text-sm font-medium rounded-lg border transition-colors min-w-[40px]',
                isCurrentPage
                  ? 'bg-blue-600 dark:bg-blue-500 text-white border-blue-600 dark:border-blue-500 shadow-sm'
                  : 'text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700 hover:border-gray-400 dark:hover:border-slate-500'
              )}
            >
              {pageNumber}
            </button>
          )
        })}
      </div>

      {/* Next Button */}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className={clsx(
          'flex items-center px-3 py-2 text-sm font-medium rounded-lg border transition-colors',
          currentPage >= totalPages
            ? 'text-gray-400 dark:text-slate-500 bg-gray-50 dark:bg-slate-700 border-gray-200 dark:border-slate-600 cursor-not-allowed'
            : 'text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700 hover:border-gray-400 dark:hover:border-slate-500'
        )}
      >
        Next
        <ChevronRight size={16} className="ml-1" />
      </button>
    </div>
  )
}
