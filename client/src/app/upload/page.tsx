'use client';

import React from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import UploadPageContent from './components/UploadPageContent';

export default function UploadPage() {
  return (
    <ProtectedRoute requireAuth={true} requireUpload={true}>
      <UploadPageContent />
    </ProtectedRoute>
  );
}