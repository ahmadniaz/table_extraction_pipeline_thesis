// src/app/context/SubmissionContext.tsx
'use client'
import React, { createContext, useContext, useState, ReactNode, useCallback } from "react";

export type FieldConfig = { field: string; label: string };

export type Submission = {
  id: string;
  companyName: string;
  fileName: string;
  fileUrl: string | null;
  tableData: any; // The DashboardTable data, for preview
  fieldConfig?: FieldConfig[]; // <-- Added for preview columns
  status: "Approved" | "Rejected";
  rejectionReason?: string;
};

type SubmissionContextType = {
  submissions: Submission[];
  addSubmission: (sub: Submission) => void;
  clearSubmissions: () => void;
  // Global refresh mechanism for dashboard data
  refreshTrigger: number;
  triggerDashboardRefresh: () => void;
};

const SubmissionContext = createContext<SubmissionContextType | undefined>(undefined);

export function SubmissionProvider({ children }: { children: ReactNode }) {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  function addSubmission(sub: Submission) {
    setSubmissions((prev) => [...prev, sub]);
  }

  function clearSubmissions() {
    setSubmissions([]);
  }

  // Global refresh mechanism for dashboard data
  const triggerDashboardRefresh = useCallback(() => {
    console.log('🔄 Triggering global dashboard refresh...');
    setRefreshTrigger(prev => prev + 1);
  }, []);

  return (
    <SubmissionContext.Provider value={{ 
      submissions, 
      addSubmission, 
      clearSubmissions,
      refreshTrigger,
      triggerDashboardRefresh
    }}>
      {children}
    </SubmissionContext.Provider>
  );
}

export function useSubmission() {
  const ctx = useContext(SubmissionContext);
  if (!ctx) throw new Error("useSubmission must be used within SubmissionProvider");
  return ctx;
}
