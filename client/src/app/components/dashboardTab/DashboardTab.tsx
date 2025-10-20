'use client'
import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import axios from 'axios';
import StatCard from "./StatCard";
import CarriersModal from "./CarriersModal";
import { useDashboardStats, useCarriers, useEarnedCommissionStats } from "../../hooks/useDashboard";
import { TrendingUp, Upload, FileText, Users, Clock, CheckCircle, XCircle } from "lucide-react";
import SummaryUploadZone from "../SummaryUploadZone";
import UnifiedTableEditor from "../upload/UnifiedTableEditor";
import toast from 'react-hot-toast';
import { useSubmission } from "@/context/SubmissionContext";

type FieldConfig = { field: string, label: string }

interface DashboardTabProps {
  showAnalytics?: boolean;
}

export default function DashboardTab({ showAnalytics = false }: DashboardTabProps) {
  const router = useRouter();
  const { refreshTrigger } = useSubmission();
  
  // Only fetch stats when analytics are needed
  const { stats, loading, refetch: refetchStats } = useDashboardStats(showAnalytics);
  const { carriers, loading: carriersLoading, fetchCarriers } = useCarriers();
  const { stats: earnedCommissionStats, loading: earnedCommissionLoading, refetch: refetchEarnedCommissionStats } = useEarnedCommissionStats(undefined, showAnalytics);
  const [carriersModalOpen, setCarriersModalOpen] = useState(false);

  // Upload and processing states - NEW 2-STEP FLOW ONLY
  const [company, setCompany] = useState<{ id: string, name: string } | null>(null);
  const [uploaded, setUploaded] = useState<any>(null);
  const [databaseFields, setDatabaseFields] = useState<FieldConfig[]>([]);
  const [loadingFields, setLoadingFields] = useState(false);
  const [showUnifiedEditor, setShowUnifiedEditor] = useState(false);
  const [savingMapping, setSavingMapping] = useState(false);
  const [planTypes, setPlanTypes] = useState<string[]>([]);
  const [selectedStatementDate, setSelectedStatementDate] = useState<any>(null);
  const [extractionMethod, setExtractionMethod] = useState('smart');

  // Refresh earned commission stats when component mounts (only if analytics are shown)
  useEffect(() => {
    if (showAnalytics) {
      refetchEarnedCommissionStats();
    }
  }, [refetchEarnedCommissionStats, showAnalytics]);

  // Listen for global refresh events (only if analytics are shown)
  useEffect(() => {
    if (showAnalytics) {
      // Add a small delay to prevent race conditions with auth refresh
      const timeoutId = setTimeout(() => {
        refetchStats();
        refetchEarnedCommissionStats();
      }, 100);
      
      return () => clearTimeout(timeoutId);
    }
  }, [refreshTrigger, refetchStats, refetchEarnedCommissionStats, showAnalytics]);

  // Load selected statement date from upload progress
  const loadSelectedStatementDate = useCallback(async () => {
    const uploadUuid = uploaded?.extraction_id || uploaded?.id || uploaded?.upload_id;
    if (uploadUuid) {
      try {
        const response = await axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/api/pending/progress/${uploadUuid}/table_editor`,
          { withCredentials: true }
        );
        if (response.data.success && response.data.progress_data?.selected_statement_date) {
          setSelectedStatementDate(response.data.progress_data.selected_statement_date);
        }
      } catch (error) {
        console.error('Error loading selected statement date:', error);
      }
    }
  }, [uploaded?.extraction_id, uploaded?.id, uploaded?.upload_id]);

  // Load selected statement date when upload changes
  useEffect(() => {
    loadSelectedStatementDate();
  }, [loadSelectedStatementDate]);

  const handleCardClick = (cardType: string) => {
    switch (cardType) {
      case 'total_statements':
        router.push('/statements');
        break;
      case 'total_carriers':
        fetchCarriers();
        setCarriersModalOpen(true);
        break;
      case 'total_earned_commission':
        router.push('/?tab=earned-commission');
        break;
      case 'pending_reviews':
        router.push('/statements?tab=pending');
        break;
      case 'approved_statements':
        router.push('/statements?tab=approved');
        break;
      case 'rejected_statements':
        router.push('/statements?tab=rejected');
        break;
      default:
        break;
    }
  };

  // Fetch database fields from backend
  useEffect(() => {
    async function fetchDatabaseFields() {
      try {
        setLoadingFields(true);
        const response = await axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/api/database-fields/?active_only=true`,
          { withCredentials: true }
        );
        const fieldsFromBackend = response.data.map((field: any) => ({
          field: field.field_key,
          label: field.display_name
        }));
        setDatabaseFields(fieldsFromBackend);
      } catch (error) {
        console.error('Error fetching database fields:', error);
        toast.error('Failed to load database fields');
      } finally {
        setLoadingFields(false);
      }
    }

    if (databaseFields.length === 0) {
      fetchDatabaseFields();
    }
  }, [databaseFields.length]);

  // Handle upload result - NEW 2-STEP FLOW
  function handleUploadResult({ tables, upload_id, extraction_id, file_name, file, plan_types, extracted_carrier, extracted_date, gcs_url, gcs_key, document_metadata, ai_intelligence, carrier_id, company_id }: any) {
    
    
    // Set uploaded data with AI intelligence and carrier information
    setUploaded({ 
      tables, 
      upload_id, 
      extraction_id: extraction_id || upload_id, 
      id: extraction_id || upload_id, 
      file_name, 
      file, 
      gcs_url, 
      gcs_key, 
      extracted_carrier,
      extracted_date,
      document_metadata,
      ai_intelligence,
      carrier_id,  // CRITICAL: Include carrier_id for AI field mapping
      company_id   // CRITICAL: Include company_id as fallback
    });
    
    // Handle carrier detection and auto-creation
    if (extracted_carrier) {
      const currentCarrierMatches = company && (
        company.name.toLowerCase().includes(extracted_carrier.toLowerCase()) ||
        extracted_carrier.toLowerCase().includes(company.name.toLowerCase())
      );
      
      if (currentCarrierMatches) {
        toast.success(`✅ Carrier verified: ${extracted_carrier}`);
      } else {
        if (company) {
          toast.success(
            `🎯 Carrier detected: "${extracted_carrier}". File has been automatically assigned to the correct carrier.`,
            { duration: 6000 }
          );
        } else {
          toast.success(
            `🎯 Carrier detected: "${extracted_carrier}". Carrier has been auto-created and file assigned.`,
            { duration: 6000 }
          );
        }
        
        setCompany({ 
          id: 'auto-detected', 
          name: extracted_carrier 
        });
      }
    }
    
    // Handle extracted date
    if (extracted_date) {
      const dateInfo = {
        date: extracted_date,
        confidence: document_metadata?.date_confidence || 0.8,
        source: 'ai_extraction'
      };
      setSelectedStatementDate(dateInfo);
      toast.success(`Auto-detected statement date: ${extracted_date}`);
    }
    
    // Set plan types
    if (plan_types) setPlanTypes(plan_types);
    
    // Open UnifiedTableEditor for the new 2-step flow
    setShowUnifiedEditor(true);
  }

  // Handle reset
  function handleReset() {
    setCompany(null);
    setUploaded(null);
    setShowUnifiedEditor(false);
    setPlanTypes([]);
    setSelectedStatementDate(null);
    setExtractionMethod('smart');
  }

  const statCards = [
    { 
      label: "Total Statements", 
      value: stats?.total_statements || 0, 
      icon: FileText,
      type: 'total_statements',
      disabled: false,
      color: 'blue' as const,
      description: 'From last month',
      gradient: 'from-blue-500 to-indigo-600'
    },
    { 
      label: "Total Carriers", 
      value: stats?.total_carriers || 0, 
      icon: Users,
      type: 'total_carriers',
      disabled: false,
      color: 'purple' as const,
      description: 'Active carriers',
      gradient: 'from-purple-500 to-violet-600'
    },
    { 
      label: "Total Earned Commission", 
      value: earnedCommissionStats?.total_commission ? `$${(earnedCommissionStats.total_commission / 1000).toFixed(1)}K` : '$0', 
      icon: TrendingUp,
      type: 'total_earned_commission',
      disabled: false,
      color: 'green' as const,
      description: 'Total commission earned',
      gradient: 'from-emerald-500 to-teal-600'
    },
    { 
      label: "Pending Reviews", 
      value: stats?.pending_reviews || 0, 
      icon: Clock,
      type: 'pending_reviews',
      disabled: false,
      color: 'amber' as const,
      description: 'Awaiting review',
      gradient: 'from-amber-500 to-orange-600'
    },
    { 
      label: "Approved Statements", 
      value: stats?.approved_statements || 0, 
      icon: CheckCircle,
      type: 'approved_statements',
      disabled: false,
      color: 'green' as const,
      description: 'Successfully processed',
      gradient: 'from-green-500 to-emerald-600'
    },
    { 
      label: "Rejected Statements", 
      value: stats?.rejected_statements || 0, 
      icon: XCircle,
      type: 'rejected_statements',
      disabled: false,
      color: 'red' as const,
      description: 'Requires attention',
      gradient: 'from-red-500 to-rose-600'
    },
  ];

  // Render UnifiedTableEditor - NEW 2-STEP FLOW
  if (showUnifiedEditor && uploaded) {

    
    return (
      <div className="fixed inset-0 bg-white dark:bg-gray-900 z-50">
        <UnifiedTableEditor
          extractedData={{
            tables: uploaded.tables || [],
            planType: uploaded.document_metadata?.plan_type,
            planTypeConfidence: uploaded.document_metadata?.plan_type_confidence,
            carrierName: uploaded.extracted_carrier,
            statementDate: uploaded.extracted_date,
            gcs_url: uploaded.gcs_url,
            file_name: uploaded.file_name,
            extracted_carrier: uploaded.extracted_carrier,
            extracted_date: uploaded.extracted_date,
            upload_id: uploaded.upload_id || uploaded.id,
            // CRITICAL FIX: Use uploaded.carrier_id (from backend) first, fallback to uploaded.company_id
            // Don't use company?.id as it might be 'auto-detected' which is not a valid UUID
            company_id: uploaded.carrier_id || uploaded.company_id || (company?.id !== 'auto-detected' ? company?.id : undefined),
            carrier_id: uploaded.carrier_id || uploaded.company_id,
            document_metadata: uploaded.document_metadata,
            ai_intelligence: uploaded.ai_intelligence
          }}
          uploadData={uploaded}
          databaseFields={databaseFields.map(f => ({
            id: f.field,
            display_name: f.label,
            description: f.label
          }))}
          selectedStatementDate={selectedStatementDate}
          onDataUpdate={(data) => {
            setUploaded((prev: any) => ({ ...prev, tables: data.tables }));
          }}
          onSubmit={async (finalData) => {
            try {
              setSavingMapping(true);
              
              // Save mappings to backend
              const config = {
                mapping: finalData.field_mappings,
                plan_types: finalData.plan_types || planTypes || [],
                field_config: databaseFields,
                table_data: uploaded.tables?.[0]?.rows || [],
                headers: uploaded.tables?.[0]?.header || [],
                selected_statement_date: selectedStatementDate
              };
              
              // Only save mapping if company is set and not a temporary ID
              if (company && company.id && !company.id.includes('temp') && !company.id.includes('auto')) {
                await axios.post(
                  `${process.env.NEXT_PUBLIC_API_URL}/api/companies/${company.id}/mapping/`,
                  config,
                  { withCredentials: true }
                );
              } else {
                console.log('⚠️ Skipping mapping save - carrier not yet persisted in database');
              }
              
              // Update local state
              setPlanTypes(finalData.plan_types || planTypes || []);
              setShowUnifiedEditor(false);
              
              toast.success('Data submitted successfully! 🎉');
              
              // Navigate back to dashboard
              setTimeout(() => {
                window.location.href = '/?tab=dashboard';
              }, 1000);
              
            } catch (error) {
              console.error('Error saving mappings:', error);
              toast.error('Failed to save mappings');
            } finally {
              setSavingMapping(false);
            }
          }}
        />
      </div>
    );
  }

  // If showing analytics, render the stats grid with hierarchy
  if (showAnalytics) {
    // Separate cards by importance
    const primaryCard = statCards.find(card => card.type === 'total_earned_commission');
    const secondaryCards = statCards.filter(card => ['total_statements', 'total_carriers'].includes(card.type));
    const tertiaryCards = statCards.filter(card => ['pending_reviews', 'approved_statements', 'rejected_statements'].includes(card.type));

    return (
      <div className="w-full space-y-8">
        {/* Primary Card - Total Earned Commission (Hero Card) */}
        {primaryCard && (
          <div className="animate-scale-in">
            <div 
              className="group relative bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-lg hover:shadow-xl p-8 transition-all duration-300 cursor-pointer hover:scale-[1.01] hover:-translate-y-1"
              onClick={() => handleCardClick(primaryCard.type)}
            >
              {/* Background Gradient Overlay */}
              <div className={`absolute inset-0 bg-gradient-to-br ${primaryCard.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-300 rounded-2xl`}></div>
              
              {/* Content */}
              <div className="relative z-10">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-4 mb-6">
                      <div className={`w-20 h-20 rounded-2xl bg-gradient-to-r ${primaryCard.gradient} flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-300`}>
                        <primaryCard.icon className="text-white" size={40} />
                      </div>
                      <div>
                        <h3 className="text-3xl font-bold text-slate-800 dark:text-slate-200 group-hover:text-slate-900 dark:group-hover:text-slate-100 transition-colors">
                          {primaryCard.label}
                        </h3>
                        <p className="text-slate-500 dark:text-slate-400 text-lg mt-1">{primaryCard.description}</p>
                      </div>
                    </div>
                    
                    <div className="text-6xl font-bold text-slate-900 dark:text-slate-100 group-hover:text-slate-900 dark:group-hover:text-slate-100 transition-colors">
                      {loading || earnedCommissionLoading ? (
                        <div className="w-48 h-16 bg-slate-200 dark:bg-slate-600 rounded animate-pulse"></div>
                      ) : primaryCard.value}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Hover Border Effect */}
              <div className={`absolute inset-0 rounded-2xl border-2 border-transparent group-hover:border-gradient-to-r ${primaryCard.gradient} opacity-0 group-hover:opacity-20 transition-all duration-300`}></div>
            </div>
          </div>
        )}

        {/* Secondary Cards - Total Statements & Total Carriers */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {secondaryCards.map((card, i) => (
            <div 
              key={card.type} 
              className="animate-scale-in"
              style={{ animationDelay: `${(i + 1) * 100}ms` }}
            >
              <div 
                className="group relative bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-lg p-6 transition-all duration-300 cursor-pointer hover:scale-[1.02] hover:-translate-y-1"
                onClick={() => handleCardClick(card.type)}
              >
                {/* Background Gradient Overlay */}
                <div className={`absolute inset-0 bg-gradient-to-br ${card.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300 rounded-xl`}></div>
                
                {/* Content */}
                <div className="relative z-10">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="font-semibold text-xl text-slate-800 dark:text-slate-200 group-hover:text-slate-800 dark:group-hover:text-slate-200 transition-colors mb-4">
                        {card.label}
                      </div>
                      
                      <div className="text-4xl font-bold text-slate-900 dark:text-slate-100 group-hover:text-slate-900 dark:group-hover:text-slate-100 transition-colors mb-2">
                        {loading ? (
                          <div className="w-28 h-10 bg-slate-200 dark:bg-slate-600 rounded animate-pulse"></div>
                        ) : card.value}
                      </div>
                      
                      <div className="text-sm text-slate-500 dark:text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 transition-colors">
                        {card.description}
                      </div>
                    </div>
                    
                    <div className={`w-16 h-16 rounded-xl bg-gradient-to-r ${card.gradient} flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-300`}>
                      <card.icon className="text-white" size={32} />
                    </div>
                  </div>
                </div>
                
                {/* Hover Border Effect */}
                <div className={`absolute inset-0 rounded-xl border-2 border-transparent group-hover:border-gradient-to-r ${card.gradient} opacity-0 group-hover:opacity-20 transition-all duration-300`}></div>
              </div>
            </div>
          ))}
        </div>

        {/* Tertiary Cards - Status Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {tertiaryCards.map((card, i) => (
            <div 
              key={card.type} 
              className="animate-scale-in"
              style={{ animationDelay: `${(i + 3) * 100}ms` }}
            >
              <StatCard 
                label={card.label} 
                value={card.value} 
                icon={card.icon}
                onClick={() => handleCardClick(card.type)}
                disabled={card.disabled}
                loading={loading || earnedCommissionLoading}
                color={card.color}
                description={card.description}
                gradient={card.gradient}
              />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <>
      {/* New Integrated Upload Interface */}
      <div className="w-full h-full min-h-[calc(100vh-200px)] p-6">
        <div className="h-full">
          <SummaryUploadZone
            onParsed={handleUploadResult}
            selectedStatementDate={selectedStatementDate}
            extractionMethod={extractionMethod}
            onExtractionMethodChange={setExtractionMethod}
          />
        </div>
      </div>

      {/* Carriers Modal */}
      <CarriersModal
        isOpen={carriersModalOpen}
        onClose={() => setCarriersModalOpen(false)}
        carriers={carriers}
        loading={carriersLoading}
      />
    </>
  );
}
