'use client';

import React from 'react';

interface LoadingScreenProps {
  message?: string;
  className?: string;
}

export default function LoadingScreen({ 
  message = "Loading...", 
  className = "min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-100/50 dark:from-slate-900 dark:via-slate-800/50 dark:to-slate-900" 
}: LoadingScreenProps) {
  return (
    <div className={className}>
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="text-center max-w-md mx-auto">
          {/* Spinner Container - Made larger */}
          <div className="relative mb-8">
            <div className="w-24 h-24 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-xl mx-auto animate-pulse">
              <img 
                src="/images/icon.svg" 
                alt="Commission Tracker Icon" 
                className="w-20 h-20 object-contain"
              />
            </div>
            {/* Animated ring around the logo */}
            <div className="absolute inset-0 w-24 h-24 border-4 border-blue-600 rounded-2xl animate-spin mx-auto"></div>
          </div>
          
          {/* Message with better centering and dark mode support */}
          <div className="space-y-2">
            <p className="text-lg font-semibold text-slate-800 dark:text-slate-200 leading-tight">
              {message}
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Please wait while we prepare everything for you...
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
