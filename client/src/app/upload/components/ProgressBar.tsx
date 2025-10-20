'use client'
import React from 'react'
import { Check } from 'lucide-react'

type ProgressStep = {
  id: string
  label: string
  status: 'completed' | 'current' | 'pending'
}

type ProgressBarProps = {
  currentStep: string
  steps?: ProgressStep[]
}

const DEFAULT_STEPS = [
  { id: 'upload', label: 'Upload', status: 'pending' as const },
  { id: 'table_editor', label: 'Process', status: 'pending' as const },
  { id: 'field_mapper', label: 'Mapping', status: 'pending' as const },
  { id: 'dashboard', label: 'Review', status: 'pending' as const }
]

const ProgressBarComponent = ({ currentStep, steps = DEFAULT_STEPS }: ProgressBarProps) => {
  // Removed console.log to prevent excessive logging on every render
  
  const getStepStatus = (stepId: string): 'completed' | 'current' | 'pending' => {
    const stepOrder = ['upload', 'table_editor', 'field_mapper', 'dashboard']
    const currentIndex = stepOrder.indexOf(currentStep)
    const stepIndex = stepOrder.indexOf(stepId)
    
    if (stepIndex < currentIndex) return 'completed'
    if (stepIndex === currentIndex) return 'current'
    return 'pending'
  }

  const updatedSteps = steps.map(step => ({
    ...step,
    status: getStepStatus(step.id)
  }))

  return (
    <div className="bg-transparent py-1 z-10 relative">
      <div className="flex items-center justify-center gap-4">
        {updatedSteps.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <div className="flex items-center gap-2">
              <div className={`
                w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold transition-all duration-300 shadow-sm
                ${step.status === 'completed' 
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg' 
                  : step.status === 'current' 
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg' 
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700'
                }
              `}>
                {step.status === 'completed' ? (
                  <Check size={14} />
                ) : (
                  index + 1
                )}
              </div>
              <span className={`
                text-xs font-medium transition-all duration-300 whitespace-nowrap
                ${step.status === 'completed' 
                  ? 'text-emerald-600 dark:text-emerald-400' 
                  : step.status === 'current' 
                  ? 'text-blue-600 dark:text-blue-400' 
                  : 'text-slate-500 dark:text-slate-400'
                }
              `}>
                {step.label}
              </span>
            </div>
            {index < updatedSteps.length - 1 && (
              <div className={`
                w-12 h-1 mx-4 transition-all duration-300 rounded-full
                ${step.status === 'completed' ? 'bg-gradient-to-r from-emerald-500 to-teal-600' : 'bg-slate-200 dark:bg-slate-700'}
              `} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
};

ProgressBarComponent.displayName = 'ProgressBar';

const ProgressBar = React.memo(ProgressBarComponent);

export default ProgressBar;
