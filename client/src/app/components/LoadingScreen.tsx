'use client';

import React from 'react';
import { FlaskConical } from 'lucide-react';

interface LoadingScreenProps {
  message?: string;
  className?: string;
}

export default function LoadingScreen({
  message = 'Loading…',
  className = 'min-h-screen bg-slate-50 dark:bg-slate-900',
}: LoadingScreenProps) {
  return (
    <div className={className}>
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="text-center">
          <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/40 rounded-2xl flex items-center justify-center mx-auto mb-4 animate-pulse">
            <FlaskConical className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
          </div>
          <p className="text-base font-medium text-slate-700 dark:text-slate-300">{message}</p>
        </div>
      </div>
    </div>
  );
}
