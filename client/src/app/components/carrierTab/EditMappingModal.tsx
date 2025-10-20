'use client'
import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import FieldMapper from '@/app/upload/components/FieldMapper'

type FieldConfig = { field: string, label: string }

export default function EditMappingModal({ 
  company, 
  onClose, 
  onSave 
}: { 
  company: { id: string, name: string }, 
  onClose: () => void, 
  onSave: (mapping: Record<string, string>, fields: FieldConfig[], planTypes: string[]) => void 
}) {
  const [fieldConfig, setFieldConfig] = useState<FieldConfig[]>([])
  const [databaseFields, setDatabaseFields] = useState<FieldConfig[]>([])
  const [loadingFields, setLoadingFields] = useState(true)
  const [mapping, setMapping] = useState<Record<string, string> | null>(null)
  const [planTypes, setPlanTypes] = useState<string[]>([])
  const [savingMapping, setSavingMapping] = useState(false)

  function getLabelFromDatabaseFields(fieldKey: string) {
    return (databaseFields.find(f => f.field === fieldKey)?.label) || fieldKey;
  }

  // Fetch database fields from backend
  useEffect(() => {
    async function fetchDatabaseFields() {
      try {
        setLoadingFields(true)
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/database-fields/?active_only=true`)
        if (response.ok) {
          const data = await response.json()
          const fieldsFromBackend = data.map((field: any) => ({
            field: field.field_key,
            label: field.display_name
          }))
          setDatabaseFields(fieldsFromBackend)
          
          // Set as default fieldConfig if not already set
          if (fieldConfig.length === 0) {
            setFieldConfig(fieldsFromBackend)
          }
        } else {
          console.error('Failed to fetch database fields')
          toast.error('Failed to load database fields')
        }
      } catch (error) {
        console.error('Error fetching database fields:', error)
        toast.error('Failed to load database fields')
      } finally {
        setLoadingFields(false)
      }
    }

    fetchDatabaseFields()
  }, [fieldConfig.length])

  // Fetch existing mapping
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/companies/${company.id}/mapping/`)
      .then(r => r.json())
      .then(mappingObj => {
        if (mappingObj && mappingObj.mapping) {
          setMapping(mappingObj.mapping)
          setFieldConfig(mappingObj.field_config || databaseFields)
          if (mappingObj.plan_types) setPlanTypes(mappingObj.plan_types)
        } else {
          setFieldConfig(databaseFields)
        }
      })
      .catch(() => setFieldConfig(databaseFields))
  }, [company.id, databaseFields])

  if (loadingFields) {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto shadow-2xl">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-slate-200 dark:border-slate-600 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-slate-600 dark:text-slate-400 font-medium">Loading database fields...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200">Edit Field Mapping</h2>
            <p className="text-slate-600 dark:text-slate-400 mt-1">Configure field mappings for {company.name}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <FieldMapper
          company={company}
          columns={[]} // Will be populated when mapping is loaded
          isLoading={savingMapping}
          onSave={async (map, fieldConf, selectedPlanTypes) => {
            setSavingMapping(true);
            try {
              await onSave(map, fieldConf, selectedPlanTypes);
              onClose();
            } catch (error) {
              console.error('Error saving mapping:', error);
              toast.error('Failed to save mapping');
            } finally {
              setSavingMapping(false);
            }
          }}
          onSkip={onClose}
          onGoToTableEditor={onClose} // Close modal when going back to table editor
          initialFields={fieldConfig}
          initialMapping={mapping}
          initialPlanTypes={planTypes}
        />
      </div>
    </div>
  )
}
