'use client'
import React, { useState, useEffect, useMemo } from 'react';
import { 
  ArrowLeft, 
  FileText, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Download, 
  Eye, 
  Search,
  ChevronLeft,
  ChevronRight,
  Building2,
  Filter
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useStatements, useCarriers } from '../hooks/useDashboard';
import StatementPreviewModal from '../components/carrierTab/StatementPreviewModal';
import axios from 'axios';

interface Statement {
  id: string;
  file_name: string;
  company_name: string;
  status: 'extracted' | 'success' | 'completed' | 'Approved' | 'rejected' | 'pending';
  uploaded_at: string;
  last_updated: string;
  completed_at?: string;
  rejection_reason?: string;
  plan_types?: string[];
  raw_data?: any;
  edited_tables?: any;
  final_data?: any;
  field_config?: any;
}

interface Carrier {
  id: string;
  name: string;
  statement_count: number;
}

export default function StatementsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'all' | 'approved' | 'rejected' | 'pending'>('all');
  const [selectedCarrier, setSelectedCarrier] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [carriersPage, setCarriersPage] = useState(1);
  const [previewStatement, setPreviewStatement] = useState<Statement | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  
  const { carriers, loading: carriersLoading, fetchCarriers } = useCarriers();
  const [allStatements, setAllStatements] = useState<Statement[]>([]);
  const [filteredStatements, setFilteredStatements] = useState<Statement[]>([]);
  const [loading, setLoading] = useState(false);
  const [statementsLoading, setStatementsLoading] = useState(true);
  
  const ITEMS_PER_PAGE = 10; // For statements
  const CARRIERS_PER_PAGE = 10; // For carriers

  // Handle URL parameters for initial tab
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    if (tabParam && ['all', 'approved', 'rejected', 'pending'].includes(tabParam)) {
      setActiveTab(tabParam as any);
    }
  }, []);

  // Fetch statements based on active tab
  useEffect(() => {
    const fetchStatements = async () => {
      setStatementsLoading(true);
      try {
        let endpoint = `${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/statements`;
        
        // Use server-side filtering for better performance and accuracy
        if (activeTab !== 'all') {
          const statusMapping = {
            'pending': 'pending',
            'approved': 'approved', 
            'rejected': 'rejected'
          };
          const statusParam = statusMapping[activeTab as keyof typeof statusMapping];
          if (statusParam) {
            endpoint = `${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/statements/${statusParam}`;
          }
        }
        
        const response = await axios.get(endpoint, {
          withCredentials: true  // CRITICAL FIX: Ensure cookies are sent
        });
        const data = response.data;
        setAllStatements(data);
        setFilteredStatements(data);
      } catch (error) {
        console.error('Error fetching statements:', error);
      } finally {
        setStatementsLoading(false);
      }
    };
    fetchStatements();
  }, [activeTab]);

  // Fetch carriers
  useEffect(() => {
    fetchCarriers();
  }, [fetchCarriers]);

  // Filter carriers based on active tab to show only carriers with statements in that status
  const filteredCarriersByTab = useMemo(() => {
    if (activeTab === 'all') {
      return carriers;
    }
    
    // Get unique company names from filtered statements
    const companyNamesWithStatements = new Set(
      filteredStatements.map(statement => statement.company_name)
    );
    
    // Filter carriers to only show those with statements in the current tab
    return carriers.filter(carrier => 
      companyNamesWithStatements.has(carrier.name)
    );
  }, [carriers, filteredStatements, activeTab]);

  // Filter carriers based on search query and tab
  const filteredCarriers = useMemo(() => {
    const baseCarriers = filteredCarriersByTab;
    
    if (!searchQuery.trim()) return baseCarriers;
    return baseCarriers.filter(carrier => 
      carrier.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [filteredCarriersByTab, searchQuery]);

  // Filter statements based on selected carrier and status
  const finalFilteredStatements = useMemo(() => {
    let filtered = filteredStatements;
    
    // Filter by carrier
    if (selectedCarrier !== 'all') {
      const selectedCarrierName = carriers.find(c => c.id === selectedCarrier)?.name;
      filtered = filtered.filter((s: Statement) => s.company_name === selectedCarrierName);
    }
    
    // Sort by latest uploaded first
    filtered.sort((a: Statement, b: Statement) => new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime());
    
    return filtered;
  }, [filteredStatements, selectedCarrier, carriers]);

  // Pagination for statements
  const totalPages = Math.ceil(finalFilteredStatements.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedStatements = finalFilteredStatements.slice(startIndex, endIndex);

  // Pagination for carriers
  const totalCarrierPages = Math.ceil(filteredCarriers.length / CARRIERS_PER_PAGE);
  const carriersStartIndex = (carriersPage - 1) * CARRIERS_PER_PAGE;
  const carriersEndIndex = carriersStartIndex + CARRIERS_PER_PAGE;
  const paginatedCarriers = filteredCarriers.slice(carriersStartIndex, carriersEndIndex);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedCarrier, activeTab]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
      case 'Approved':
        return <CheckCircle className="text-green-500" size={20} />;
      case 'rejected':
        return <XCircle className="text-red-500" size={20} />;
      case 'extracted':
      case 'success':
      case 'pending':
        return <Clock className="text-yellow-500" size={20} />;
      default:
        return <FileText className="text-gray-500" size={20} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
      case 'Approved':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'rejected':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'extracted':
      case 'success':
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handlePreview = async (statement: Statement) => {
    // Check if the statement already has final_data and field_config (from dashboard API)
    if (statement.final_data && statement.field_config) {
      // Data is already available, no need for API call
      setPreviewStatement(statement);
      return;
    }

    // If final_data or field_config is not available, fetch it from the statements API
    setPreviewLoading(true);
    try {
      // Find the carrier ID from the carriers list
      const carrier = carriers.find(c => c.name === statement.company_name);
      
      if (carrier) {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/companies/${carrier.id}/statements/`);
        if (response.ok) {
          const statements = await response.json();
          const fullStatement = statements.find((s: any) => s.id === statement.id);
          if (fullStatement) {
            // Ensure we have the complete data structure
            const completeStatement = {
              ...statement,
              final_data: fullStatement.final_data || statement.final_data,
              field_config: fullStatement.field_config || statement.field_config,
              raw_data: fullStatement.raw_data || statement.raw_data,
              plan_types: fullStatement.plan_types || statement.plan_types
            };
            setPreviewStatement(completeStatement);
          } else {
            console.error('Statement not found in company statements');
          }
        } else {
          console.error('Failed to fetch company statements');
        }
      } else {
        console.error('Carrier not found');
      }
    } catch (error) {
      console.error('Error fetching statement details:', error);
    } finally {
      setPreviewLoading(false);
    }
  };

  const getStatusCounts = (carrierId: string) => {
    const carrierName = carriers.find(c => c.id === carrierId)?.name;
    const carrierStatements = carrierId === 'all' 
      ? allStatements 
      : allStatements.filter(s => s.company_name === carrierName);
    
    return {
      all: carrierStatements.length,
      approved: carrierStatements.filter(s => ['completed', 'Approved'].includes(s.status)).length,
      rejected: carrierStatements.filter(s => s.status === 'rejected').length,
      pending: carrierStatements.filter(s => ['extracted', 'success', 'pending'].includes(s.status)).length,
    };
  };

  const statusCounts = getStatusCounts(selectedCarrier);

  const tabs = [
    { id: 'all', label: 'All', count: statusCounts.all },
    { id: 'approved', label: 'Approved', count: statusCounts.approved },
    { id: 'rejected', label: 'Rejected', count: statusCounts.rejected },
    { id: 'pending', label: 'Pending', count: statusCounts.pending },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex h-screen">
        {/* Sidebar */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <button
                onClick={() => router.back()}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft size={20} className="text-gray-600" />
              </button>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Statements</h1>
                <p className="text-sm text-gray-500">Manage your statements</p>
              </div>
            </div>
            
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
              <input
                type="text"
                placeholder="Search carriers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Carriers List */}
          <div className="flex-1 overflow-y-auto">
            {carriersLoading ? (
              <div className="p-6 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="text-sm text-gray-500 mt-2">Loading carriers...</p>
              </div>
            ) : (
              <>
                {/* All Carriers Option */}
                <div className="p-4">
                  <button
                    onClick={() => setSelectedCarrier('all')}
                    className={`w-full flex items-center justify-between p-3 rounded-lg transition-all ${
                      selectedCarrier === 'all'
                        ? 'bg-blue-50 border border-blue-200 text-blue-700'
                        : 'hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Building2 size={20} className="text-blue-600" />
                      <span className="font-medium">All Carriers</span>
                    </div>
                    <span className="bg-gray-200 text-gray-700 px-2 py-1 rounded-full text-xs font-medium">
                      {allStatements.length}
                    </span>
                  </button>
                </div>

                {/* Individual Carriers */}
                <div className="px-4 space-y-2">
                  {paginatedCarriers.map((carrier) => (
                    <button
                      key={carrier.id}
                      onClick={() => setSelectedCarrier(carrier.id)}
                      className={`w-full flex items-center justify-between p-3 rounded-lg transition-all ${
                        selectedCarrier === carrier.id
                          ? 'bg-blue-50 border border-blue-200 text-blue-700'
                          : 'hover:bg-gray-50 text-gray-700'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                          <span className="text-white text-sm font-bold">
                            {carrier.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="text-left">
                          <div className="font-medium truncate max-w-32">{carrier.name}</div>
                          <div className="text-xs text-gray-500">{carrier.statement_count} statements</div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>

                {/* Carriers Pagination */}
                {totalCarrierPages > 1 && (
                  <div className="p-4 border-t border-gray-200">
                    <div className="flex items-center justify-between">
                      <button
                        onClick={() => setCarriersPage(Math.max(1, carriersPage - 1))}
                        disabled={carriersPage === 1}
                        className="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ChevronLeft size={16} />
                      </button>
                      <span className="text-sm text-gray-600">
                        {carriersPage} of {totalCarrierPages}
                      </span>
                      <button
                        onClick={() => setCarriersPage(Math.min(totalCarrierPages, carriersPage + 1))}
                        disabled={carriersPage === totalCarrierPages}
                        className="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="bg-white border-b border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {selectedCarrier === 'all' 
                    ? 'All Carriers' 
                    : carriers.find(c => c.id === selectedCarrier)?.name
                  }
                </h2>
                <p className="text-gray-600">
                  {finalFilteredStatements.length} statement{finalFilteredStatements.length !== 1 ? 's' : ''} found
                </p>
              </div>
              
              {/* Status Tabs */}
              <div className="flex bg-gray-100 rounded-lg p-1">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                      activeTab === tab.id
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {tab.label}
                      <span className="bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full text-xs">
                        {tab.count}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading || statementsLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="text-gray-600 mt-4">Loading statements...</p>
                </div>
              </div>
            ) : paginatedStatements.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <FileText className="mx-auto text-gray-400" size={48} />
                  <h3 className="text-xl font-semibold text-gray-600 mt-4">No statements found</h3>
                  <p className="text-gray-500 mt-2">
                    {selectedCarrier === 'all' 
                      ? 'No statements match the current filters.'
                      : `No statements found for this carrier with ${activeTab} status.`
                    }
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {paginatedStatements.map((statement) => (
                  <div key={statement.id} className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-all">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4 flex-1">
                        <div className="mt-1">
                          {getStatusIcon(statement.status)}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="font-semibold text-gray-900 truncate">{statement.file_name}</h3>
                            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(statement.status)}`}>
                              {statement.status === 'extracted' || statement.status === 'success' || statement.status === 'pending' ? 'Pending' :
                               statement.status === 'completed' || statement.status === 'Approved' ? 'Approved' :
                               statement.status === 'rejected' ? 'Rejected' :
                               statement.status}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
                            <span>Uploaded: {formatDate(statement.uploaded_at)}</span>
                            {statement.completed_at && (
                              <span>Completed: {formatDate(statement.completed_at)}</span>
                            )}
                          </div>
                          
                          {statement.plan_types && statement.plan_types.length > 0 && (
                            <div className="flex gap-2 mb-3">
                              {statement.plan_types.map((plan, index) => (
                                <span
                                  key={index}
                                  className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-md border border-blue-200"
                                >
                                  {plan}
                                </span>
                              ))}
                            </div>
                          )}
                          
                          {statement.rejection_reason && (
                            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                              <p className="text-sm text-red-700">
                                <strong>Rejection Reason:</strong> {statement.rejection_reason}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 ml-4">
                        {/* Show eye icon only for approved/rejected statements */}
                        {(statement.status === 'completed' || statement.status === 'Approved' || statement.status === 'rejected') && (
                          <button
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            title="View details"
                            onClick={() => handlePreview(statement)}
                          >
                            <Eye size={16} className="text-gray-500" />
                          </button>
                        )}
                        <button
                          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                          title="Download"
                        >
                          <Download size={16} className="text-gray-500" />
                        </button>
                        {(statement.status === 'extracted' || statement.status === 'success' || statement.status === 'pending') && (
                          <button
                            onClick={() => router.push(`/upload?resume=${statement.id}`)}
                            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors font-medium"
                          >
                            Complete Review
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Statements Pagination */}
          {totalPages > 1 && (
            <div className="bg-white border-t border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  Showing {startIndex + 1} to {Math.min(endIndex, finalFilteredStatements.length)} of {finalFilteredStatements.length} statements
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  
                  <div className="flex gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      const pageNum = i + 1;
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`px-3 py-1 rounded-lg text-sm font-medium ${
                            currentPage === pageNum
                              ? 'bg-blue-600 text-white'
                              : 'text-gray-600 hover:bg-gray-100'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>
                  
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Statement Preview Modal */}
      {previewStatement && (
        <StatementPreviewModal
          statement={previewStatement}
          onClose={() => setPreviewStatement(null)}
        />
      )}

      {/* Preview Loading Modal */}
      {previewLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 flex items-center gap-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="text-gray-700">Loading statement preview...</span>
          </div>
        </div>
      )}
    </div>
  );
} 