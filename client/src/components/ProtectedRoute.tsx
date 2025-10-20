'use client';

import React, { ReactNode } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Shield, AlertCircle } from 'lucide-react';
import LoadingScreen from '@/app/components/LoadingScreen';

interface ProtectedRouteProps {
  children: ReactNode;
  requireAuth?: boolean;
  requireAdmin?: boolean;
  requireUpload?: boolean;
  requireEdit?: boolean;
  fallback?: ReactNode;
}

export default function ProtectedRoute({
  children,
  requireAuth = true,
  requireAdmin = false,
  requireUpload = false,
  requireEdit = false,
  fallback
}: ProtectedRouteProps) {
  const { user, permissions, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    if (requireAuth && !isAuthenticated) {
      console.log('ProtectedRoute: Not authenticated, redirecting to landing');
      router.push('/landing');
      return;
    }

    if (requireAdmin && user?.role !== 'admin') {
      console.log('ProtectedRoute: Not admin, redirecting to home');
      router.push('/');
      return;
    }

    if (requireUpload && permissions && !permissions.can_upload) {
      console.log('ProtectedRoute: No upload permission, redirecting to home');
      router.push('/');
      return;
    }

    if (requireEdit && permissions && !permissions.can_edit) {
      console.log('ProtectedRoute: No edit permission, redirecting to home');
      router.push('/');
      return;
    }
  }, [isAuthenticated, user, permissions, isLoading, requireAuth, requireAdmin, requireUpload, requireEdit, router]);

  if (isLoading) {
    return <LoadingScreen message="Loading Commission Tracker..." />;
  }

  if (requireAuth && !isAuthenticated) {
    return null; // Will redirect to login
  }

  if (requireAdmin && user?.role !== 'admin') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md mx-auto p-6"
        >
          <Shield className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600 mb-6">
            You don&apos;t have permission to access this page. Admin access is required.
          </p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go to Dashboard
          </button>
        </motion.div>
      </div>
    );
  }

  if (requireUpload && permissions && !permissions.can_upload) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md mx-auto p-6"
        >
          <AlertCircle className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Upload Restricted</h1>
          <p className="text-gray-600 mb-6">
            You don&apos;t have permission to upload files. Please contact your administrator.
          </p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go to Dashboard
          </button>
        </motion.div>
      </div>
    );
  }

  if (requireEdit && permissions && !permissions.can_edit) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md mx-auto p-6"
        >
          <AlertCircle className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Edit Restricted</h1>
          <p className="text-gray-600 mb-6">
            You have read-only access. You cannot edit data. Please contact your administrator.
          </p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go to Dashboard
          </button>
        </motion.div>
      </div>
    );
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
