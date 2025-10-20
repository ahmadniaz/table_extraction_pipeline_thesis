'use client'
import React, { useState, useEffect, useCallback } from 'react'
import { Plus, Edit, Trash2, Save, X, ChevronLeft, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'

type PlanType = {
  id: string
  display_name: string
  description?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

type PlanTypeCreate = {
  display_name: string
  description?: string
  is_active: boolean
}

type PlanTypeUpdate = {
  plan_key?: string
  display_name?: string
  description?: string
  is_active?: boolean
}

export default function PlanTypesManager() {
  const [planTypes, setPlanTypes] = useState<PlanType[]>([])
  const [loading, setLoading] = useState(true)
  const [editingPlanType, setEditingPlanType] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<PlanTypeUpdate>({})
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createForm, setCreateForm] = useState<PlanTypeCreate>({
    display_name: '',
    description: '',
    is_active: true
  })
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  const totalPages = Math.ceil(planTypes.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const paginatedPlanTypes = planTypes.slice(startIndex, endIndex)

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  // Fetch plan types
  const fetchPlanTypes = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/plan-types/?active_only=true`)
      if (!response.ok) throw new Error('Failed to fetch plan types')
      const data = await response.json()
      setPlanTypes(data)
    } catch (error) {
      toast.error('Failed to load plan types')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPlanTypes()
  }, [fetchPlanTypes])



  // Create plan type
  const createPlanType = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/plan-types/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createForm)
      })
      if (!response.ok) throw new Error('Failed to create plan type')
      toast.success('Plan type created successfully!')
      setShowCreateForm(false)
      setCreateForm({ display_name: '', description: '', is_active: true })
      fetchPlanTypes()
    } catch (error) {
      toast.error('Failed to create plan type')
      console.error(error)
    }
  }

  // Update plan type
  const updatePlanType = async (planTypeId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/plan-types/${planTypeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm)
      })
      if (!response.ok) throw new Error('Failed to update plan type')
      toast.success('Plan type updated successfully!')
      setEditingPlanType(null)
      setEditForm({})
      fetchPlanTypes()
    } catch (error) {
      toast.error('Failed to update plan type')
      console.error(error)
    }
  }

  // Delete plan type
  const deletePlanType = async (planTypeId: string) => {
    if (!confirm('Are you sure you want to delete this plan type?')) return
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/plan-types/${planTypeId}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error('Failed to delete plan type')
      toast.success('Plan type deleted successfully!')
      fetchPlanTypes()
    } catch (error) {
      toast.error('Failed to delete plan type')
      console.error(error)
    }
  }

  // Start editing
  const startEdit = (planType: PlanType) => {
    setEditingPlanType(planType.id)
    setEditForm({
      display_name: planType.display_name,
      description: planType.description,
      is_active: planType.is_active
    })
  }

  // Cancel editing
  const cancelEdit = () => {
    setEditingPlanType(null)
    setEditForm({})
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 border-2 border-slate-200 border-t-blue-500 rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 dark:text-slate-200">Plan Types</h1>
          <p className="text-slate-600 dark:text-slate-400 mt-2">Manage the plan types used for insurance categorization</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
          >
            <Plus size={18} />
            Add Plan Type
          </button>
        </div>
      </div>

      {/* Create Form Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 w-full max-w-md shadow-2xl">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200 mb-6">Create New Plan Type</h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Display Name</label>
                <input
                  type="text"
                  value={createForm.display_name}
                  onChange={(e) => setCreateForm({ ...createForm, display_name: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
                  placeholder="e.g., Medical"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Description</label>
                <textarea
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
                  rows={3}
                  placeholder="Optional description"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="create-active"
                  checked={createForm.is_active}
                  onChange={(e) => setCreateForm({ ...createForm, is_active: e.target.checked })}
                  className="mr-3 w-4 h-4 text-emerald-600 bg-slate-100 dark:bg-slate-700 border-slate-300 dark:border-slate-600 rounded focus:ring-emerald-500"
                />
                <label htmlFor="create-active" className="text-sm font-medium text-slate-700 dark:text-slate-300">Active</label>
              </div>
            </div>
            <div className="flex gap-4 mt-8">
              <button
                onClick={createPlanType}
                className="flex-1 px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
              >
                Create
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                className="flex-1 px-6 py-3 bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-300 rounded-xl font-semibold hover:bg-slate-300 dark:hover:bg-slate-500 transition-all duration-200"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Plan Types Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full company-table">
            <thead className="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-bold text-slate-800 dark:text-slate-200">Display Name</th>
                <th className="px-6 py-4 text-left text-sm font-bold text-slate-800 dark:text-slate-200">Description</th>
                <th className="px-6 py-4 text-left text-sm font-bold text-slate-800 dark:text-slate-200">Status</th>
                <th className="px-6 py-4 text-left text-sm font-bold text-slate-800 dark:text-slate-200">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {paginatedPlanTypes.map((planType) => (
                <tr key={planType.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                  <td className="px-6 py-4">
                    {editingPlanType === planType.id ? (
                      <input
                        type="text"
                        value={editForm.display_name || ''}
                        onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                        className="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
                      />
                    ) : (
                      <span className="font-semibold text-slate-800 dark:text-slate-200">{planType.display_name}</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {editingPlanType === planType.id ? (
                      <textarea
                        value={editForm.description || ''}
                        onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                        className="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
                        rows={2}
                      />
                    ) : (
                      <span className="text-slate-600 dark:text-slate-400 text-sm">{planType.description || '-'}</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {editingPlanType === planType.id ? (
                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          checked={editForm.is_active ?? planType.is_active}
                          onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                          className="mr-3 w-4 h-4 text-emerald-600 bg-slate-100 dark:bg-slate-700 border-slate-300 dark:border-slate-600 rounded focus:ring-emerald-500"
                        />
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Active</span>
                      </div>
                    ) : (
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
                        planType.is_active 
                          ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800' 
                          : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800'
                      }`}>
                        {planType.is_active ? 'Active' : 'Inactive'}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {editingPlanType === planType.id ? (
                      <div className="flex gap-2">
                        <button
                          onClick={() => updatePlanType(planType.id)}
                          className="p-2 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 rounded-lg transition-colors"
                          title="Save"
                        >
                          <Save size={16} />
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-600 rounded-lg transition-colors"
                          title="Cancel"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          onClick={() => startEdit(planType)}
                          className="p-2 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 rounded-lg transition-colors"
                          title="Edit"
                        >
                          <Edit size={16} />
                        </button>
                        <button
                          onClick={() => deletePlanType(planType.id)}
                          className="p-2 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/30">
            <div className="text-sm text-slate-700 dark:text-slate-300">
              Showing {startIndex + 1} to {Math.min(endIndex, planTypes.length)} of {planTypes.length} plan types
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="flex items-center gap-1 px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                          ? 'bg-emerald-500 text-white shadow-sm'
                          : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
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
                className="flex items-center gap-1 px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
        
        {planTypes.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-500 dark:text-slate-400">No plan types found.</p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="mt-4 px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
            >
              Add Your First Plan Type
            </button>
          </div>
        )}
      </div>
    </div>
  )
} 