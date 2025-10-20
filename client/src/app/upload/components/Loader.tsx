import React from 'react';

interface LoaderProps {
  message?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'spinner' | 'dots' | 'pulse' | 'bars';
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'destructive';
}

const LoaderComponent = ({ 
  message = "Loading...", 
  className = '', 
  size = 'md',
  variant = 'spinner',
  color = 'primary'
}: LoaderProps) => {
  // Removed console.log to prevent excessive logging on every render
  
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
  }
  
  const colorClasses = {
    primary: 'border-blue-500',
    secondary: 'border-purple-500',
    success: 'border-emerald-500',
    warning: 'border-amber-500',
    destructive: 'border-red-500'
  }
  
  return (
    <div className={`flex items-center justify-center py-12 ${className}`}>
      <div className="flex items-center gap-3">
        <div className={`animate-spin rounded-full border-2 border-slate-200 border-t-current ${sizeClasses[size]} ${colorClasses[color]}`}></div>
        <span className="text-slate-600 font-medium">{message}</span>
      </div>
    </div>
  )
};

LoaderComponent.displayName = 'Loader';

const Loader = React.memo(LoaderComponent);

export default Loader;

// Specialized loader components for different use cases
export function TableLoader({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center py-12 ${className}`}>
      <div className="flex items-center gap-3">
        <div className="w-6 h-6 border-2 border-slate-200 border-t-blue-500 rounded-full animate-spin"></div>
        <span className="text-slate-600 font-medium">Loading data...</span>
      </div>
    </div>
  );
}

export function CardLoader({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center py-8 ${className}`}>
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-slate-200 border-t-blue-500 rounded-full animate-spin"></div>
        <span className="text-slate-600 font-medium">Loading...</span>
      </div>
    </div>
  );
}

export function ButtonLoader({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
      <span className="font-medium">Loading...</span>
    </div>
  );
}

export function SkeletonLoader({ className = '', lines = 3 }: { className?: string; lines?: number }) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div 
          key={i} 
          className="h-4 bg-slate-200 rounded-lg animate-pulse"
          style={{ animationDelay: `${i * 100}ms` }}
        ></div>
      ))}
    </div>
  );
} 