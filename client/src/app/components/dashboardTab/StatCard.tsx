import { FileText, Database, User, AlertCircle, TrendingUp, Users, Clock, CheckCircle, XCircle } from "lucide-react";
import React from "react";

type Props = {
  label: string;
  value: string | number | null;
  icon: string | React.ComponentType<any>;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  color?: 'blue' | 'purple' | 'green' | 'red' | 'amber' | 'gray';
  description?: string;
  gradient?: string;
};

const icons = { 
  FileText, 
  Database, 
  User, 
  AlertCircle, 
  TrendingUp, 
  Users, 
  Clock, 
  CheckCircle, 
  XCircle 
};

const colorClasses = {
  blue: 'text-primary-600',
  purple: 'text-secondary-600',
  green: 'text-success-600',
  red: 'text-destructive-600',
  amber: 'text-warning-600',
  gray: 'text-gray-400'
};

const bgColorClasses = {
  blue: 'bg-primary-50',
  purple: 'bg-secondary-50',
  green: 'bg-success-50',
  red: 'bg-destructive-50',
  amber: 'bg-warning-50',
  gray: 'bg-gray-50'
};

export default function StatCard({ 
  label, 
  value, 
  icon, 
  onClick, 
  disabled = false, 
  loading = false,
  color = 'blue',
  description,
  gradient = 'from-primary-500 to-primary-600'
}: Props) {
  const Icon = typeof icon === 'string' ? (icons as any)[icon] || FileText : icon;
  
  const handleClick = () => {
    if (!disabled && !loading && onClick) {
      onClick();
    }
  };

      const cardClasses = `
        group relative bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-lg p-6
        transition-all duration-300 cursor-pointer
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02] hover:-translate-y-1'}
      `;

  return (
    <div 
      className={cardClasses}
      onClick={handleClick}
      title={disabled ? "Coming soon" : undefined}
    >
      {/* Background Gradient Overlay */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300 rounded-xl`}></div>
      
      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className={`font-semibold text-sm ${disabled ? 'text-slate-500 dark:text-slate-400' : 'text-slate-800 dark:text-slate-200'} group-hover:text-slate-800 dark:group-hover:text-slate-200 transition-colors mb-2`}>
              {label}
            </div>
            
            <div className={`text-3xl font-bold ${disabled ? 'text-slate-500 dark:text-slate-400' : 'text-slate-900 dark:text-slate-100'} group-hover:text-slate-900 dark:group-hover:text-slate-100 transition-colors`}>
              {loading ? (
                <div className="w-20 h-6 bg-slate-200 dark:bg-slate-600 rounded animate-pulse"></div>
              ) : disabled ? '—' : value}
            </div>
            
            {description && (
              <div className={`text-xs ${disabled ? 'text-slate-500 dark:text-slate-400' : 'text-slate-500 dark:text-slate-400'} group-hover:text-slate-600 dark:group-hover:text-slate-300 transition-colors mt-1`}>
                {description}
              </div>
            )}
          </div>
          
          <div className={`w-12 h-12 rounded-xl bg-gradient-to-r ${gradient} flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-300`}>
            <Icon className="text-white" size={24} />
          </div>
        </div>
        
        
            {/* Disabled Indicator */}
            {disabled && (
              <div className="absolute bottom-4 right-4 flex items-center gap-1 px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded-full">
                <AlertCircle className="text-slate-500 dark:text-slate-400" size={14} />
                <span className="text-slate-500 dark:text-slate-400 text-xs font-medium">Coming Soon</span>
              </div>
            )}
      </div>
      
      {/* Hover Border Effect */}
      <div className={`absolute inset-0 rounded-xl border-2 border-transparent group-hover:border-gradient-to-r ${gradient} opacity-0 group-hover:opacity-20 transition-all duration-300`}></div>
    </div>
  );
}
