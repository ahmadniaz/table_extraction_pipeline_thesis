'use client'

import { Toaster as HotToaster } from 'react-hot-toast'

export function Toaster() {
  return (
    <HotToaster
      position="top-center"
      toastOptions={{
        duration: 3500,
        style: {
          fontSize: '1rem',
          borderRadius: '0.75rem',
          background: '#fff',
          color: '#222',
          boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
          padding: '1rem 1.5rem',
        },
        success: {
          iconTheme: {
            primary: '#22c55e',
            secondary: '#fff',
          },
          style: {
            background: '#e6f9ed',
            color: '#166534',
          },
        },
        error: {
          iconTheme: {
            primary: '#ef4444',
            secondary: '#fff',
          },
          style: {
            background: '#fee2e2',
            color: '#991b1b',
          },
        },
        loading: {
          iconTheme: {
            primary: '#3b82f6',
            secondary: '#fff',
          },
          style: {
            background: '#dbeafe',
            color: '#1e40af',
          },
        },
      }}
    />
  )
}
