'use client'
import React, { useState, useMemo, useEffect, useCallback } from 'react';
import {
  DollarSign,
  Building2,
  TrendingUp,
  Users,
  Search,
  ChevronRight,
  FileText,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
  Download,
  Edit,
  ChevronLeft,
  Menu,
  Sparkles,
  BarChart3,
  RefreshCw,
  X,
  SlidersHorizontal,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  ArrowRight
} from 'lucide-react';
import EditCommissionModal from './EditCommissionModal';
import MergeConfirmationModal from './MergeConfirmationModal';
import CompanyCarrierModal from './CompanyCarrierModal';
import { CompanyNameNormalizer } from '../../utils/CompanyNameNormalizer';
import { 
  useEarnedCommissionStats, 
  useGlobalEarnedCommissionStats,
  useGlobalCommissionData,
  useCarriersWithCommission, 
  useCarrierCommissionStats, 
  useCarrierCommissionData,
  useAllCommissionData,
  useAvailableYears
} from '../../hooks/useDashboard';
import { useSubmission } from '@/context/SubmissionContext';

interface CarrierDetail {
  carrier_name: string;
  commission_earned: number;
  invoice_total: number;
  statement_count: number;
  statement_year?: number;
}

interface CommissionData {
  id: string;
  carrier_name?: string;
  client_name: string;
  invoice_total: number;
  commission_earned: number;
  statement_count: number;
  upload_ids?: string[];
  approved_statement_count?: number;
  statement_date?: string;
  statement_month?: number;
  statement_year?: number;
  monthly_breakdown?: {
    jan: number;
    feb: number;
    mar: number;
    apr: number;
    may: number;
    jun: number;
    jul: number;
    aug: number;
    sep: number;
    oct: number;
    nov: number;
    dec: number;
  };
  last_updated?: string;
  created_at?: string;
  carrierDetails?: CarrierDetail[];
  carrierCount?: number;
}

interface CarrierGroup {
  carrierName: string;
  companies: CommissionData[];
  totalCommission: number;
  totalInvoice: number;
  companyCount: number;
  statementCount: number;
}

interface CarrierCardProps {
  carrierGroup: CarrierGroup;
  isExpanded: boolean;
  showMonthlyDetails: boolean;
  onToggleExpand: () => void;
  onToggleMonthlyDetails: () => void;
  onEditCompany: (data: CommissionData) => void;
  viewAllData: boolean;
}


// Component definitions for the new full-width table view

const CarrierCard: React.FC<CarrierCardProps> = ({ 
  carrierGroup, 
  isExpanded, 
  showMonthlyDetails, 
  onToggleExpand, 
  onToggleMonthlyDetails, 
  onEditCompany,
  viewAllData 
}) => {
  
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };
  
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-all duration-300">
      {/* Card Header */}
      <div 
        className="p-4 md:p-6 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors duration-200"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onToggleExpand(); // This should call toggleCarrierExpansion(carrierGroup.carrierName)
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onToggleExpand();
          }
        }}
        aria-expanded={isExpanded}
        aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${carrierGroup.carrierName} details`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 md:gap-4 min-w-0 flex-1">
            {/* Carrier Logo Placeholder */}
            <div className="w-10 h-10 md:w-12 md:h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white font-bold text-sm md:text-lg flex-shrink-0">
              {carrierGroup.carrierName.charAt(0).toUpperCase()}
            </div>
            
            {/* Carrier Info */}
            <div className="min-w-0 flex-1">
              <h3 className="text-lg md:text-xl font-bold text-slate-800 dark:text-slate-200 truncate">{carrierGroup.carrierName}</h3>
              <p className="text-xs md:text-sm text-slate-600 dark:text-slate-400">{carrierGroup.companyCount} companies • {carrierGroup.statementCount} statements</p>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="text-right ml-2">
            <p className="text-lg md:text-2xl font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(carrierGroup.totalCommission)}</p>
            <p className="text-xs md:text-sm text-slate-600 dark:text-slate-400 hidden md:block">Total Commission</p>
            <p className="text-xs text-slate-500 dark:text-slate-500 hidden lg:block">Invoice: {formatCurrency(carrierGroup.totalInvoice)}</p>
          </div>

          {/* Expand/Collapse Icon */}
          <div className="ml-2 flex-shrink-0">
            {isExpanded ? (
              <ChevronUp className="w-5 h-5 md:w-6 md:h-6 text-slate-400 dark:text-slate-500" />
            ) : (
              <ChevronDown className="w-5 h-5 md:w-6 md:h-6 text-slate-400 dark:text-slate-500" />
            )}
          </div>
        </div>
      </div>

      {/* Card Content - Simple clickable card, no expansion */}
      <div className="px-4 md:px-6 pb-4 md:pb-6">
        <div className="pt-2">
          <div className="text-xs text-slate-500 dark:text-slate-400 text-center">
            Click to view all {carrierGroup.companyCount} companies
          </div>
        </div>
      </div>
    </div>
  );
};

const CarrierFullTableView: React.FC<{
  carrier: CarrierGroup;
  onBack: () => void;
  onEditCompany: (data: CommissionData) => void;
  viewAllData: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  expandedCompanies: Set<string>;
  onToggleCompanyExpansion: (companyId: string) => void;
}> = ({ 
  carrier, 
  onBack, 
  onEditCompany, 
  viewAllData, 
  searchQuery, 
  onSearchChange,
  expandedCompanies,
  onToggleCompanyExpansion 
}) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  // Filter companies based on search
  const filteredCompanies = useMemo(() => {
    if (!searchQuery) return carrier.companies;
    return carrier.companies.filter(company => 
      company.client_name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [carrier.companies, searchQuery]);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
      {/* Header with Back Button */}
      <div className="p-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <ChevronLeft size={16} />
              Back to Carriers
            </button>
            <div className="h-6 w-px bg-slate-300 dark:bg-slate-600" />
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
                {carrier.carrierName.charAt(0).toUpperCase()}
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-800 dark:text-slate-200">{carrier.carrierName}</h2>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {carrier.companyCount} companies • {formatCurrency(carrier.totalCommission)} total commission
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 dark:text-slate-500" size={16} />
          <input
            type="text"
            placeholder={`Search companies in ${carrier.carrierName}...`}
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
          />
        </div>
      </div>

      {/* Companies Table */}
      <div className="overflow-x-auto">
        <table className="w-full company-table">
          <thead className="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="text-left py-3 px-6 font-semibold text-slate-700 dark:text-slate-300">Company Name</th>
              <th className="text-right py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Total Commission</th>
              <th className="text-right py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Total Invoice</th>
              <th className="text-center py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Statements</th>
              <th className="text-center py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredCompanies.map((company) => (
              <React.Fragment key={company.id}>
                {/* Company Row */}
                <tr 
                  className="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                  onClick={() => onToggleCompanyExpansion(company.id)}
                >
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-3">
                      {expandedCompanies.has(company.id) ? (
                        <ChevronDown size={16} className="text-slate-400 dark:text-slate-500" />
                      ) : (
                        <ChevronRight size={16} className="text-slate-400 dark:text-slate-500" />
                      )}
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-slate-200">{company.client_name}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">Year: {company.statement_year || 'N/A'}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-4 text-right">
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(company.commission_earned)}</span>
                  </td>
                  <td className="py-4 px-4 text-right">
                    <span className="font-medium text-slate-700 dark:text-slate-300">{formatCurrency(company.invoice_total)}</span>
                  </td>
                  <td className="py-4 px-4 text-center">
                    <span className="text-slate-600 dark:text-slate-400">{company.statement_count}</span>
                  </td>
                  <td className="py-4 px-4 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onEditCompany(company);
                      }}
                      disabled={viewAllData}
                      className={`p-2 rounded-lg transition-colors ${ 
                        viewAllData 
                          ? 'text-slate-400 dark:text-slate-600 cursor-not-allowed opacity-50' 
                          : 'text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30'
                      }`}
                      title={viewAllData ? 'Read-only mode - switch to My Data to edit' : 'Edit commission data'}
                    >
                      <Edit size={16} />
                    </button>
                  </td>
                </tr>

                {/* Expanded Monthly Breakdown Row */}
                {expandedCompanies.has(company.id) && (
                  <tr>
                    <td colSpan={5} className="py-4 px-6 bg-slate-50 dark:bg-slate-700/30">
                      <div className="space-y-3">
                        <h4 className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                          <BarChart3 size={16} />
                          Monthly Breakdown for {company.client_name}
                        </h4>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm company-table">
                            <thead>
                              <tr className="border-b border-slate-200 dark:border-slate-600">
                                {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map(month => (
                                  <th key={month} className="text-center py-2 px-3 font-medium text-slate-600 dark:text-slate-400 min-w-[80px]">
                                    {month}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              <tr>
                                {['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'].map(month => (
                                  <td key={month} className="text-center py-2 px-3 text-slate-700 dark:text-slate-300">
                                    {company.monthly_breakdown?.[month as keyof typeof company.monthly_breakdown] 
                                      ? formatCurrency(company.monthly_breakdown[month as keyof typeof company.monthly_breakdown])
                                      : '-'
                                    }
                                  </td>
                                ))}
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/30">
        <div className="flex items-center justify-between text-sm text-slate-600 dark:text-slate-400">
          <span>Showing {filteredCompanies.length} of {carrier.companyCount} companies</span>
          <span className="font-medium">
            Total Commission: <span className="text-emerald-600 dark:text-emerald-400 font-bold">{formatCurrency(carrier.totalCommission)}</span>
          </span>
        </div>
      </div>
    </div>
  );
};

// Carriers List Modal Component
const CarriersListModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  carriers: CarrierGroup[];
}> = ({ isOpen, onClose, carriers }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  // Filter and sort carriers alphabetically
  const filteredCarriers = useMemo(() => {
    const filtered = carriers.filter(carrier =>
      carrier.carrierName.toLowerCase().includes(searchQuery.toLowerCase())
    );
    return filtered.sort((a, b) => a.carrierName.localeCompare(b.carrierName));
  }, [carriers, searchQuery]);

  // Pagination
  const totalPages = Math.ceil(filteredCarriers.length / ITEMS_PER_PAGE);
  const paginatedCarriers = filteredCarriers.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  // Reset page when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
              <Building2 className="text-purple-600 dark:text-purple-400" size={24} />
              All Carriers
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X size={20} className="text-slate-500 dark:text-slate-400" />
            </button>
          </div>
          
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 dark:text-slate-500" size={16} />
            <input
              type="text"
              placeholder="Search carriers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all duration-200"
            />
          </div>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-200px)]">
          {paginatedCarriers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-500 dark:text-slate-400">
              <Building2 className="text-slate-300 dark:text-slate-600 mb-4" size={48} />
              <p className="text-lg font-medium">No carriers found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {paginatedCarriers.map((carrier, index) => (
                <div
                  key={carrier.carrierName}
                  className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors border border-slate-200 dark:border-slate-600"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                      {carrier.carrierName.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-slate-800 dark:text-slate-200 truncate">{carrier.carrierName}</h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {carrier.companyCount} companies • {carrier.statementCount} statements
                      </p>
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <p className="font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(carrier.totalCommission)}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Total Commission</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal Footer with Pagination */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/30">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Showing {Math.min((currentPage - 1) * ITEMS_PER_PAGE + 1, filteredCarriers.length)} - {Math.min(currentPage * ITEMS_PER_PAGE, filteredCarriers.length)} of {filteredCarriers.length}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="p-2 rounded-lg border border-slate-200 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ArrowLeft size={16} className="text-slate-600 dark:text-slate-400" />
              </button>
              <span className="text-sm text-slate-600 dark:text-slate-400 px-3">
                Page {currentPage} of {totalPages || 1}
              </span>
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages || totalPages === 0}
                className="p-2 rounded-lg border border-slate-200 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ArrowRight size={16} className="text-slate-600 dark:text-slate-400" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Companies List Modal Component
const CompaniesListModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  data: CommissionData[];
  onCompanyClick?: (company: { client_name: string; carriers: CarrierDetail[] }) => void;
}> = ({ isOpen, onClose, data, onCompanyClick }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  // Normalize and aggregate companies with carrier tracking
  const normalizedCompanies = useMemo(() => {
    // Step 1: Group by exact core name
    const companiesMap = new Map<string, {
      normalizedName: string;
      originalNames: Set<string>;
      commission_earned: number;
      invoice_total: number;
      statement_count: number;
      carrierDetails: CarrierDetail[];
      id: string;
      coreName: string;
    }>();
    
    data.forEach(item => {
      // CRITICAL: Use core name (without suffix) as the grouping key
      const coreName = CompanyNameNormalizer.getCoreName(item.client_name).trim();
      const normalizedName = CompanyNameNormalizer.normalize(item.client_name);
      const carrierName = item.carrier_name || 'Unknown Carrier';
      
      if (!companiesMap.has(coreName)) {
        companiesMap.set(coreName, {
          normalizedName,
          originalNames: new Set([item.client_name]),
          commission_earned: item.commission_earned,
          invoice_total: item.invoice_total,
          statement_count: item.statement_count,
          carrierDetails: [{
            carrier_name: carrierName,
            commission_earned: item.commission_earned,
            invoice_total: item.invoice_total,
            statement_count: item.statement_count,
            statement_year: item.statement_year
          }],
          id: item.id,
          coreName
        });
      } else {
        const existing = companiesMap.get(coreName)!;
        existing.originalNames.add(item.client_name);
        existing.commission_earned += item.commission_earned;
        existing.invoice_total += item.invoice_total;
        existing.statement_count += item.statement_count;
        
        // Update to the longest/most complete normalized name
        if (normalizedName.length > existing.normalizedName.length) {
          existing.normalizedName = normalizedName;
        }
        
        // Check if carrier already exists for this company
        const existingCarrierIndex = existing.carrierDetails.findIndex(
          c => c.carrier_name === carrierName
        );
        
        if (existingCarrierIndex >= 0) {
          // Aggregate existing carrier
          existing.carrierDetails[existingCarrierIndex].commission_earned += item.commission_earned;
          existing.carrierDetails[existingCarrierIndex].invoice_total += item.invoice_total;
          existing.carrierDetails[existingCarrierIndex].statement_count += item.statement_count;
        } else {
          // Add new carrier
          existing.carrierDetails.push({
            carrier_name: carrierName,
            commission_earned: item.commission_earned,
            invoice_total: item.invoice_total,
            statement_count: item.statement_count,
            statement_year: item.statement_year
          });
        }
      }
    });
    
    // Step 2: OPTIMIZED similarity merging - only compare companies with same prefix
    // This reduces O(n²) to O(n) by grouping first
    const companiesArray = Array.from(companiesMap.values());
    
    // Group by first 3 characters for efficient comparison
    const prefixGroups = new Map<string, typeof companiesArray>();
    companiesArray.forEach(company => {
      const prefix = company.coreName.substring(0, 3).toLowerCase();
      if (!prefixGroups.has(prefix)) {
        prefixGroups.set(prefix, []);
      }
      prefixGroups.get(prefix)!.push(company);
    });
    
    // Merge within each prefix group (much smaller groups!)
    const merged: typeof companiesArray = [];
    prefixGroups.forEach(group => {
      const processed = new Set<number>();
      
      group.forEach((company, i) => {
        if (processed.has(i)) return;
        
        // Start a new merged company
        const mergedCompany = { ...company };
        processed.add(i);
        
        // Only compare within this small prefix group
        group.forEach((otherCompany, j) => {
          if (j <= i || processed.has(j)) return;
          
          const similarity = CompanyNameNormalizer.calculateSimilarity(
            company.coreName,
            otherCompany.coreName
          );
          
          // Merge if highly similar (handles "Advanced Carrier Ser" vs "Advanced Carrier Services")
          if (similarity >= 0.85) {
            // Merge into group
            mergedCompany.commission_earned += otherCompany.commission_earned;
            mergedCompany.invoice_total += otherCompany.invoice_total;
            mergedCompany.statement_count += otherCompany.statement_count;
            
            // Use the longest name
            if (otherCompany.normalizedName.length > mergedCompany.normalizedName.length) {
              mergedCompany.normalizedName = otherCompany.normalizedName;
            }
            
            // Merge original names
            otherCompany.originalNames.forEach(name => mergedCompany.originalNames.add(name));
            
            // Merge carriers
            otherCompany.carrierDetails.forEach(otherCarrier => {
              const existingCarrierIndex = mergedCompany.carrierDetails.findIndex(
                c => c.carrier_name === otherCarrier.carrier_name
              );
              
              if (existingCarrierIndex >= 0) {
                mergedCompany.carrierDetails[existingCarrierIndex].commission_earned += otherCarrier.commission_earned;
                mergedCompany.carrierDetails[existingCarrierIndex].invoice_total += otherCarrier.invoice_total;
                mergedCompany.carrierDetails[existingCarrierIndex].statement_count += otherCarrier.statement_count;
              } else {
                mergedCompany.carrierDetails.push({ ...otherCarrier });
              }
            });
            
            processed.add(j);
          }
        });
        
        merged.push(mergedCompany);
      });
    });
    
    // Convert to final format and sort
    return merged
      .map(company => ({
        id: company.id,
        client_name: company.normalizedName,
        commission_earned: company.commission_earned,
        invoice_total: company.invoice_total,
        statement_count: company.statement_count,
        carrierDetails: company.carrierDetails,
        carrierCount: company.carrierDetails.length,
        carrier_name: company.carrierDetails.map(c => c.carrier_name).join(', ')
      }))
      .sort((a, b) => a.client_name.localeCompare(b.client_name));
  }, [data]);

  // Filter companies
  const filteredCompanies = useMemo(() => {
    return normalizedCompanies.filter(company =>
      company.client_name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [normalizedCompanies, searchQuery]);

  // Pagination
  const totalPages = Math.ceil(filteredCompanies.length / ITEMS_PER_PAGE);
  const paginatedCompanies = filteredCompanies.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  // Reset page when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
              <Users className="text-orange-600 dark:text-orange-400" size={24} />
              All Companies
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X size={20} className="text-slate-500 dark:text-slate-400" />
            </button>
          </div>
          
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 dark:text-slate-500" size={16} />
            <input
              type="text"
              placeholder="Search companies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all duration-200"
            />
          </div>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-200px)]">
          {paginatedCompanies.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-500 dark:text-slate-400">
              <Users className="text-slate-300 dark:text-slate-600 mb-4" size={48} />
              <p className="text-lg font-medium">No companies found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {paginatedCompanies.map((company) => (
                <div
                  key={company.id}
                  className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors border border-slate-200 dark:border-slate-600 cursor-pointer"
                  onClick={() => {
                    if (onCompanyClick && company.carrierDetails) {
                      onCompanyClick({
                        client_name: company.client_name,
                        carriers: company.carrierDetails
                      });
                    }
                  }}
                >
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-800 dark:text-slate-200 truncate">{company.client_name}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {company.carrierCount || 0} carrier{(company.carrierCount || 0) !== 1 ? 's' : ''} • {company.statement_count} statements
                    </p>
                  </div>
                  <div className="text-right ml-4">
                    <p className="font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(company.commission_earned)}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Invoice: {formatCurrency(company.invoice_total)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal Footer with Pagination */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/30">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Showing {Math.min((currentPage - 1) * ITEMS_PER_PAGE + 1, filteredCompanies.length)} - {Math.min(currentPage * ITEMS_PER_PAGE, filteredCompanies.length)} of {filteredCompanies.length}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="p-2 rounded-lg border border-slate-200 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ArrowLeft size={16} className="text-slate-600 dark:text-slate-400" />
              </button>
              <span className="text-sm text-slate-600 dark:text-slate-400 px-3">
                Page {currentPage} of {totalPages || 1}
              </span>
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages || totalPages === 0}
                className="p-2 rounded-lg border border-slate-200 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ArrowRight size={16} className="text-slate-600 dark:text-slate-400" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function EarnedCommissionTab() {
  const { refreshTrigger } = useSubmission();
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState<keyof CommissionData>('client_name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingData, setEditingData] = useState<CommissionData | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [mergeData, setMergeData] = useState<{
    existingRecord: CommissionData;
    newData: { client_name: string; invoice_total: number; commission_earned: number };
    sourceId: string;
  } | null>(null);
  const [mergeLoading, setMergeLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [carrierFilter, setCarrierFilter] = useState<string>('');
  const [minCommissionFilter, setMinCommissionFilter] = useState<string>('');
  const [maxCommissionFilter, setMaxCommissionFilter] = useState<string>('');
  const [selectedYear, setSelectedYear] = useState<number | null>(2025);
  const [viewAllData, setViewAllData] = useState(false);
  
  // NEW state for carrier interface (simplified)
  const [expandedCarriers, setExpandedCarriers] = useState<Set<string>>(new Set());
  
  // NEW state for full-width table view
  const [selectedCarrierForFullView, setSelectedCarrierForFullView] = useState<string | null>(null);
  const [expandedCompanies, setExpandedCompanies] = useState<Set<string>>(new Set());
  const [carrierCompanySearch, setCarrierCompanySearch] = useState('');
  
  // Modal states
  const [carriersModalOpen, setCarriersModalOpen] = useState(false);
  const [companiesModalOpen, setCompaniesModalOpen] = useState(false);
  const [selectedCompanyForCarriers, setSelectedCompanyForCarriers] = useState<{
    client_name: string;
    carriers: CarrierDetail[];
  } | null>(null);

  // Fetch data - use different endpoints based on view toggle
  const { stats: userStats, loading: userStatsLoading, refetch: refetchUserStats } = useEarnedCommissionStats(selectedYear || undefined);
  const { stats: globalStats, loading: globalStatsLoading, refetch: refetchGlobalStats } = useGlobalEarnedCommissionStats(selectedYear || undefined);
  const { data: userData, loading: userDataLoading, refetch: refetchUserData } = useAllCommissionData(selectedYear || undefined);
  const { data: globalData, loading: globalDataLoading, refetch: refetchGlobalData } = useGlobalCommissionData(selectedYear || undefined);
  const { carriers, loading: carriersLoading, refetch: refetchCarriers } = useCarriersWithCommission();
  const { years: availableYears, loading: yearsLoading, refetch: refetchYears } = useAvailableYears();

  // Use the appropriate data based on view toggle
  const overallStats = viewAllData ? globalStats : userStats;
  const statsLoading = viewAllData ? globalStatsLoading : userStatsLoading;
  const allData = viewAllData ? globalData : userData;
  const allDataLoading = viewAllData ? globalDataLoading : userDataLoading;

  // Calculate normalized companies count using core names
  const normalizedCompaniesCount = useMemo(() => {
    if (!allData) return 0;
    
    const companiesMap = new Map<string, boolean>();
    allData.forEach(item => {
      // Use core name to group companies with/without suffixes
      const coreName = CompanyNameNormalizer.getCoreName(item.client_name);
      companiesMap.set(coreName, true);
    });
    
    return companiesMap.size;
  }, [allData]);

  // Refresh all data
  const refreshAllData = useCallback(() => {
    if (viewAllData) {
      refetchGlobalStats();
      refetchGlobalData();
    } else {
      refetchUserStats();
      refetchUserData();
    }
    refetchCarriers();
    refetchYears();
  }, [viewAllData, refetchGlobalStats, refetchGlobalData, refetchUserStats, refetchUserData, refetchCarriers, refetchYears]);

  // Listen for global refresh events only
  useEffect(() => {
    if (refreshTrigger) {
      refreshAllData();
    }
  }, [refreshTrigger, refreshAllData]);

  const ITEMS_PER_PAGE = 20;

  // Filter and sort data
  const filteredData = useMemo(() => {
    let data = allData || [];
    
    // Note: The backend already filters data based on user role and view permissions
    // viewAllData toggle is for UI indication only - the actual filtering happens on the backend
    
    // Filter by search query (company name or carrier name)
    if (searchQuery) {
      data = data.filter((item: CommissionData) =>
        item.client_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.carrier_name && item.carrier_name.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }

    // Filter by carrier
    if (carrierFilter) {
      data = data.filter((item: CommissionData) =>
        item.carrier_name && item.carrier_name.toLowerCase().includes(carrierFilter.toLowerCase())
      );
    }

    // Filter by commission range
    if (minCommissionFilter) {
      const minCommission = parseFloat(minCommissionFilter);
      if (!isNaN(minCommission)) {
        data = data.filter((item: CommissionData) => item.commission_earned >= minCommission);
      }
    }

    if (maxCommissionFilter) {
      const maxCommission = parseFloat(maxCommissionFilter);
      if (!isNaN(maxCommission)) {
        data = data.filter((item: CommissionData) => item.commission_earned <= maxCommission);
      }
    }
    
    // Sort data - default to alphabetical by company name
    data.sort((a: CommissionData, b: CommissionData) => {
      const aValue = a[sortField];
      const bValue = b[sortField];
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      return 0;
    });
    
    return data;
  }, [allData, searchQuery, sortField, sortDirection, carrierFilter, minCommissionFilter, maxCommissionFilter]);

  // NEW: Transform data into carrier groups
  const carrierGroups = useMemo(() => {
    const groups = filteredData.reduce((groups, item: CommissionData) => {
      const carrierName = item.carrier_name || 'Unknown Carrier';
      if (!groups[carrierName]) {
        groups[carrierName] = [];
      }
      groups[carrierName].push(item);
      return groups;
    }, {} as Record<string, CommissionData[]>);

    return Object.entries(groups).map(([carrierName, companies]) => {
      const typedCompanies = companies as CommissionData[];
      // Count unique companies by client_name (normalized)
      const uniqueCompanies = new Set(typedCompanies.map(c => c.client_name.toLowerCase().trim()));
      // Get approved statement count from first record (all records from same carrier have same count)
      const approvedStatementCount = typedCompanies[0]?.approved_statement_count || 0;
      
      return {
        carrierName,
        companies: typedCompanies,
        totalCommission: typedCompanies.reduce((sum: number, company: CommissionData) => sum + company.commission_earned, 0),
        totalInvoice: typedCompanies.reduce((sum: number, company: CommissionData) => sum + company.invoice_total, 0),
        companyCount: uniqueCompanies.size, // Count unique companies (normalized), not all records
        statementCount: approvedStatementCount, // Count approved uploaded files from backend
      };
    }).sort((a, b) => b.totalCommission - a.totalCommission); // Sort by total commission descending
  }, [filteredData]);

  // Pagination
  const totalPages = Math.ceil(filteredData.length / ITEMS_PER_PAGE);
  const paginatedData = filteredData.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  // Handle sorting
  const handleSort = (field: keyof CommissionData) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      // Set default direction based on field type
      const isStringField = field === 'client_name' || field === 'carrier_name';
      setSortDirection(isStringField ? 'asc' : 'desc');
    }
    setCurrentPage(1);
  };

  // Handle edit commission data
  const handleEditCommission = (data: CommissionData) => {
    setEditingData(data);
    setEditModalOpen(true);
  };

  const handleSaveCommission = async (updatedData: Partial<CommissionData>) => {
    setEditLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/${updatedData.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_name: updatedData.client_name,
          invoice_total: updatedData.invoice_total,
          commission_earned: updatedData.commission_earned,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update commission data');
      }

      const result = await response.json();

      // Check if merge confirmation is required
      if (result.requires_merge_confirmation) {
        setMergeData({
          existingRecord: result.existing_record,
          newData: result.new_data,
          sourceId: updatedData.id!
        });
        setMergeModalOpen(true);
        setEditModalOpen(false);
        return;
      }

      // Refresh the data
      window.location.reload();
    } catch (error) {
      console.error('Error updating commission data:', error);
      alert('Failed to update commission data. Please try again.');
    } finally {
      setEditLoading(false);
    }
  };

  const handleConfirmMerge = async () => {
    if (!mergeData) return;
    
    setMergeLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/merge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_id: mergeData.sourceId,
          target_id: mergeData.existingRecord.id,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to merge commission records');
      }

      // Close modal and refresh data
      setMergeModalOpen(false);
      setMergeData(null);
      window.location.reload();
    } catch (error) {
      console.error('Error merging commission records:', error);
      alert('Failed to merge commission records. Please try again.');
    } finally {
      setMergeLoading(false);
    }
  };

  const handleCancelMerge = () => {
    setMergeModalOpen(false);
    setMergeData(null);
    setEditModalOpen(true); // Reopen the edit modal
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchQuery('');
    setCarrierFilter('');
    setMinCommissionFilter('');
    setMaxCommissionFilter('');
    setSelectedYear(2025);
    setCurrentPage(1);
  };

  // NEW: Carrier management functions
  const toggleCarrierExpansion = useCallback((carrierName: string) => {
    if (selectedCarrierForFullView === carrierName) {
      // Currently in full view - collapse back to cards
      setSelectedCarrierForFullView(null);
      setCarrierCompanySearch('');
      setExpandedCompanies(new Set());
    } else {
      // Expand to full view
      setSelectedCarrierForFullView(carrierName);
      setCarrierCompanySearch('');
      setExpandedCompanies(new Set());
    }
  }, [selectedCarrierForFullView]);


  // NEW: Company expansion handler for full table view
  const toggleCompanyExpansion = useCallback((companyId: string) => {
    setExpandedCompanies(prev => {
      const newSet = new Set(prev);
      if (newSet.has(companyId)) {
        newSet.delete(companyId);
      } else {
        newSet.add(companyId);
      }
      return newSet;
    });
  }, []);

  // Debug logs to help troubleshoot

  // Check if any filters are active
  const hasActiveFilters = searchQuery || carrierFilter || minCommissionFilter || maxCommissionFilter || selectedYear !== 2025;

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  // Format monthly value - show dash for 0, currency for non-zero values
  const formatMonthlyValue = (value: number | undefined | null) => {
    if (value === undefined || value === null || value === 0) {
      return '-';
    }
    return formatCurrency(value);
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };


  return (
    <div className="w-full space-y-6 bg-slate-50 dark:bg-slate-900 min-h-screen" style={{
      '--primary-blue': '#3B82F6',
      '--success-green': '#10B981',
      '--warning-orange': '#F59E0B',
      '--neutral-gray': '#6B7280',
      '--background-white': '#FFFFFF',
      '--card-background': '#F9FAFB',
      '--border-color': '#E5E7EB'
    } as React.CSSProperties}>
      {/* Controls */}
      <div className="flex justify-between items-center">
        {/* View Toggle */}
        <div className="flex items-center gap-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-1">
          <button
            onClick={() => setViewAllData(false)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              !viewAllData
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <Eye className="w-4 h-4" />
            My Data
          </button>
          <button
            onClick={() => setViewAllData(true)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              viewAllData
                ? 'bg-blue-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <EyeOff className="w-4 h-4" />
            All Data
          </button>
        </div>

        {/* Refresh Button */}
        <button
          onClick={refreshAllData}
          disabled={statsLoading || carriersLoading || allDataLoading}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white rounded-lg font-medium shadow-sm hover:bg-emerald-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw size={16} className={statsLoading || carriersLoading || allDataLoading ? 'animate-spin' : ''} />
          Refresh Data
        </button>
      </div>

      {/* Status Indicators */}
      {selectedYear && selectedYear !== 2025 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
              <span className="text-blue-600 dark:text-blue-400 text-sm">📅</span>
            </div>
            <div>
              <p className="text-sm font-medium text-blue-800 dark:text-blue-300">Year Filter Active</p>
              <p className="text-xs text-blue-600 dark:text-blue-400">Showing data for year {selectedYear}</p>
            </div>
          </div>
        </div>
      )}
      {viewAllData && (
        <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-600 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-amber-100 dark:bg-amber-800/60 rounded-full flex items-center justify-center">
              <span className="text-amber-600 dark:text-amber-200 text-sm">🔒</span>
            </div>
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-100">Read-Only Mode</p>
              <p className="text-xs text-amber-600 dark:text-amber-200">Viewing all company data</p>
            </div>
          </div>
        </div>
      )}

      

      {/* Stats Cards */}
      <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-600 dark:text-slate-400 text-sm">Total Invoice Amount</p>
              <div className="font-bold text-slate-800 dark:text-slate-200 text-2xl">
                {statsLoading ? (
                  <div className="w-20 h-6 bg-slate-200 dark:bg-slate-600 rounded animate-pulse"></div>
                ) : formatCurrency(overallStats?.total_invoice || 0)}
              </div>
            </div>
            <div className="bg-blue-100 dark:bg-blue-900/30 rounded-lg p-3">
              <DollarSign className="text-blue-600 dark:text-blue-400" size={24} />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-600 dark:text-slate-400 text-sm">Total Commission Earned</p>
              <div className="font-bold text-emerald-600 dark:text-emerald-400 text-2xl">
                {statsLoading ? (
                  <div className="w-20 h-6 bg-slate-200 dark:bg-slate-600 rounded animate-pulse"></div>
                ) : formatCurrency(overallStats?.total_commission || 0)}
              </div>
            </div>
            <div className="bg-emerald-100 dark:bg-emerald-900/30 rounded-lg p-3">
              <TrendingUp className="text-emerald-600 dark:text-emerald-400" size={24} />
            </div>
          </div>
        </div>

        <div 
          className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6 cursor-pointer hover:shadow-lg hover:border-purple-300 dark:hover:border-purple-600 transition-all duration-200"
          onClick={() => setCarriersModalOpen(true)}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-600 dark:text-slate-400 text-sm">Total Carriers</p>
              <p className="font-bold text-purple-600 dark:text-purple-400 text-2xl">
                {statsLoading ? (
                  <span className="w-20 h-6 bg-slate-200 dark:bg-slate-600 rounded animate-pulse inline-block"></span>
                ) : overallStats?.total_carriers || 0}
              </p>
            </div>
            <div className="bg-purple-100 dark:bg-purple-900/30 rounded-lg p-3">
              <Building2 className="text-purple-600 dark:text-purple-400" size={24} />
            </div>
          </div>
        </div>

        <div 
          className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6 cursor-pointer hover:shadow-lg hover:border-orange-300 dark:hover:border-orange-600 transition-all duration-200"
          onClick={() => setCompaniesModalOpen(true)}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-600 dark:text-slate-400 text-sm">Total Companies</p>
              <p className="font-bold text-orange-600 dark:text-orange-400 text-2xl">
                {statsLoading || allDataLoading ? (
                  <span className="w-20 h-6 bg-slate-200 dark:bg-slate-600 rounded animate-pulse inline-block"></span>
                ) : normalizedCompaniesCount}
              </p>
            </div>
            <div className="bg-orange-100 dark:bg-orange-900/30 rounded-lg p-3">
              <Users className="text-orange-600 dark:text-orange-400" size={24} />
            </div>
          </div>
        </div>
      </div>

      {/* Carrier-Centric Dashboard */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        {/* Dashboard Header */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                <BarChart3 className="text-emerald-600 dark:text-emerald-400" size={18} />
                Commission Data by Carrier
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                {carrierGroups.length} carriers • {overallStats?.total_statements || 0} total statements
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200 ${
                  showFilters 
                    ? 'bg-emerald-500 text-white shadow-sm' 
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                }`}
              >
                <SlidersHorizontal size={14} />
                <span className="text-sm font-medium">Filters</span>
                {(minCommissionFilter || maxCommissionFilter) && (
                  <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                )}
              </button>
              <button className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-all duration-200">
                <Download size={16} />
              </button>
            </div>
          </div>

          {/* Search and Filter Row */}
          <div className="space-y-4 mb-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 dark:text-slate-500" size={16} />
                <input
                  type="text"
                  placeholder="Search by company..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
                />
              </div>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 dark:text-slate-500" size={16} />
                <input
                  type="text"
                  placeholder="Search by carrier..."
                  value={carrierFilter}
                  onChange={(e) => setCarrierFilter(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
                />
              </div>
              <div>
                <select
                  value={selectedYear || 2025}
                  onChange={(e) => setSelectedYear(e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-4 py-2 text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
                >
                  <option value="" className="bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100">All Years</option>
                  {yearsLoading ? (
                    <option value="" disabled className="bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100">Loading years...</option>
                  ) : (
                    availableYears.map((year) => (
                      <option key={year} value={year} className="bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100">{year}</option>
                    ))
                  )}
                </select>
              </div>
            </div>
            
            {/* Clear Filters Button */}
            {hasActiveFilters && (
              <div className="flex justify-center">
                <button
                  onClick={clearFilters}
                  className="flex items-center gap-2 px-3 py-1 text-sm bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors font-medium"
                >
                  <X size={14} />
                  Clear All Filters
                </button>
              </div>
            )}
          </div>

          {/* Advanced Filters Panel */}
          {showFilters && (
            <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 mb-4 border border-slate-200 dark:border-slate-600">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-medium text-slate-800 dark:text-slate-200 flex items-center gap-2">
                  <Filter size={14} />
                  Advanced Filters
                </h4>
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="flex items-center gap-1 px-2 py-1 text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                  >
                    <X size={10} />
                    Clear All
                  </button>
                )}
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">Min Commission</label>
                  <input
                    type="number"
                    placeholder="Min amount..."
                    value={minCommissionFilter}
                    onChange={(e) => setMinCommissionFilter(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">Max Commission</label>
                  <input
                    type="number"
                    placeholder="Max amount..."
                    value={maxCommissionFilter}
                    onChange={(e) => setMaxCommissionFilter(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Conditional Rendering: Full Table View OR Card Grid View */}
        <div className="p-6">
          {selectedCarrierForFullView ? (
            // FULL TABLE VIEW MODE
            <CarrierFullTableView
              carrier={carrierGroups.find(c => c.carrierName === selectedCarrierForFullView)!}
              onBack={() => {
                setSelectedCarrierForFullView(null);
                setCarrierCompanySearch('');
                setExpandedCompanies(new Set());
              }}
              onEditCompany={handleEditCommission}
              viewAllData={viewAllData}
              searchQuery={carrierCompanySearch}
              onSearchChange={setCarrierCompanySearch}
              expandedCompanies={expandedCompanies}
              onToggleCompanyExpansion={toggleCompanyExpansion}
            />
          ) : (
            // CARD GRID VIEW MODE (existing code)
            <>
              {allDataLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 border-2 border-slate-200 dark:border-slate-600 border-t-emerald-500 rounded-full animate-spin"></div>
                    <span className="text-slate-500 dark:text-slate-400">Loading commission data...</span>
                  </div>
                </div>
              ) : carrierGroups.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-slate-500 dark:text-slate-400">
                  <BarChart3 className="text-slate-300 dark:text-slate-600 mb-4" size={48} />
                  <p className="text-lg font-medium mb-2">No commission data found</p>
                  {hasActiveFilters && (
                    <button
                      onClick={clearFilters}
                      className="text-sm text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 underline"
                    >
                      Clear filters to see all data
                    </button>
                  )}
                </div>
              ) : (
                <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                  {carrierGroups.map(carrierGroup => (
                    <CarrierCard
                      key={carrierGroup.carrierName}
                      carrierGroup={carrierGroup}
                      isExpanded={false} // Always false in card mode
                      showMonthlyDetails={false} // Not used in card mode
                      onToggleExpand={() => toggleCarrierExpansion(carrierGroup.carrierName)} // Now opens full table
                      onToggleMonthlyDetails={() => {}} // Not used anymore
                      onEditCompany={handleEditCommission}
                      viewAllData={viewAllData}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Summary Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/30">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-700 dark:text-slate-300 font-medium">
              Showing {carrierGroups.length} carriers with {overallStats?.total_statements || 0} total statements
            </div>
            <div className="flex items-center gap-4 text-sm text-slate-600 dark:text-slate-400">
              <span>Total Commission: <span className="font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(carrierGroups.reduce((sum, group) => sum + group.totalCommission, 0))}</span></span>
              <span>Total Invoice: <span className="font-bold text-slate-800 dark:text-slate-200">{formatCurrency(carrierGroups.reduce((sum, group) => sum + group.totalInvoice, 0))}</span></span>
            </div>
          </div>
        </div>
      </div>

      {/* Edit Commission Modal */}
      <EditCommissionModal
        isOpen={editModalOpen}
        onClose={() => {
          setEditModalOpen(false);
          setEditingData(null);
        }}
        data={editingData}
        onSave={handleSaveCommission}
        loading={editLoading}
      />

      {/* Merge Confirmation Modal */}
      {mergeData?.existingRecord && mergeData?.newData && (
        <MergeConfirmationModal
          isOpen={mergeModalOpen}
          onClose={() => {
            setMergeModalOpen(false);
            setMergeData(null);
          }}
          existingRecord={mergeData.existingRecord}
          newData={mergeData.newData}
          onConfirmMerge={handleConfirmMerge}
          onCancel={handleCancelMerge}
          loading={mergeLoading}
        />
      )}

      {/* Carriers List Modal */}
      <CarriersListModal
        isOpen={carriersModalOpen}
        onClose={() => setCarriersModalOpen(false)}
        carriers={carrierGroups}
      />

      {/* Companies List Modal */}
      <CompaniesListModal
        isOpen={companiesModalOpen}
        onClose={() => setCompaniesModalOpen(false)}
        data={allData || []}
        onCompanyClick={(company) => {
          setSelectedCompanyForCarriers(company);
          setCompaniesModalOpen(false);
        }}
      />

      {/* Company Carrier Modal */}
      {selectedCompanyForCarriers && (
        <CompanyCarrierModal
          isOpen={!!selectedCompanyForCarriers}
          onClose={() => setSelectedCompanyForCarriers(null)}
          onBack={() => {
            setSelectedCompanyForCarriers(null);
            setCompaniesModalOpen(true);
          }}
          companyName={selectedCompanyForCarriers.client_name}
          carriers={selectedCompanyForCarriers.carriers}
        />
      )}
    </div>
  );
}
