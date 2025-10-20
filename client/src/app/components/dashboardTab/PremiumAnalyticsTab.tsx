'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp, DollarSign, Building2, Calendar,
  ArrowUpRight, ArrowDownRight, Filter, Download,
  Sparkles, BarChart3, PieChart, LineChart, Target,
  Award, CheckCircle, ChevronDown, Settings,
  ExternalLink, RefreshCw, Eye, Search, SlidersHorizontal,
  HelpCircle
} from 'lucide-react';

// Import your existing hooks
import { 
  useEarnedCommissionStats, 
  useDashboardStats, 
  useAvailableYears, 
  useAllCommissionData,
  useCarriersWithCommission,
  useCarrierPieChartData
} from '../../hooks/useDashboard';

// Import utilities
import { 
  identifyTopPerformingCarriers, 
  extractMonthlyData, 
  calculateCommissionGrowth, 
  formatCurrency as utilFormatCurrency, 
  formatPercentage 
} from '../../utils/analyticsUtils';

// Chart.js imports
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';

// Import Premium Carrier Pie Chart
import PremiumCarrierPieChart from './PremiumCarrierPieChart';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Info Tooltip Component
function InfoTooltip({ content }: { content: string }) {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div className="relative inline-block">
      <button
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        onClick={() => setIsOpen(!isOpen)}
        className="p-1 text-slate-400 hover:text-blue-600 transition-colors focus:outline-none"
        aria-label="Chart information"
      >
        <HelpCircle className="w-4 h-4" />
      </button>
      
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute z-50 top-full right-0 mt-2 w-72 p-3 bg-slate-900 text-white text-xs rounded-lg shadow-xl border border-slate-700"
          style={{ transform: 'translateX(0)' }}
        >
          <div className="flex items-start space-x-2">
            <HelpCircle className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <p className="leading-relaxed">{content}</p>
          </div>
          {/* Arrow */}
          <div className="absolute -top-1 right-4 w-2 h-2 bg-slate-900 border-t border-l border-slate-700 transform rotate-45" />
        </motion.div>
      )}
    </div>
  );
}

// Individual Chart Filter Component
function ChartFilter({ 
  title, 
  options, 
  value, 
  onChange, 
  icon: Icon,
  placeholder = "All"
}: {
  title?: string;
  options: Array<{ value: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
  icon?: React.ComponentType<{ className?: string }>;
  placeholder?: string;
}) {
  return (
    <div className="flex items-center space-x-2">
      {Icon && <Icon className="w-4 h-4 text-slate-500 dark:text-slate-400" />}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-xs border-none bg-transparent text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 focus:outline-none focus:text-slate-900 dark:focus:text-slate-100 font-medium cursor-pointer pr-6"
      >
        <option value="" className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">{placeholder}</option>
        {options.map(option => (
          <option key={option.value} value={option.value} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// Enhanced Chart Wrapper with Individual Filters
function ChartWrapper({ 
  title, 
  subtitle, 
  icon: Icon, 
  gradient, 
  children, 
  filters = [],
  actions = [],
  loading = false,
  className = "",
  infoText
}: {
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  gradient: string;
  children: React.ReactNode;
  filters?: React.ReactNode[];
  actions?: Array<{
    icon: React.ComponentType<{ className?: string }>;
    title: string;
    onClick: () => void;
  }>;
  loading?: boolean;
  className?: string;
  infoText?: string;
}) {
  return (
    <div className={`bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all duration-300 ${className}`}>
      {/* Enhanced Header with Individual Filters */}
      <div className="p-4 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`w-10 h-10 bg-gradient-to-r ${gradient} rounded-xl flex items-center justify-center shadow-lg`}>
              <Icon className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h3>
                {infoText && <InfoTooltip content={infoText} />}
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>
            </div>
          </div>
          
          {/* Chart-specific filters and actions */}
          <div className="flex items-center space-x-4">
            {/* Individual Chart Filters */}
            {filters.length > 0 && (
              <div className="flex items-center space-x-3 px-3 py-1 bg-slate-50 dark:bg-slate-700 rounded-lg">
                {filters.map((filter, index) => (
                  <React.Fragment key={index}>
                    {index > 0 && <div className="w-px h-4 bg-slate-300 dark:bg-slate-600" />}
                    {filter}
                  </React.Fragment>
                ))}
              </div>
            )}
            
            {/* Chart Actions */}
            <div className="flex items-center space-x-2">
              {actions.map((action, index) => (
                <button
                  key={index}
                  onClick={action.onClick}
                  className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                  title={action.title}
                >
                  <action.icon className="w-4 h-4" />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Chart Content */}
      <div className="p-4">
        {loading ? (
          <div className="h-80 flex items-center justify-center">
            <div className="flex flex-col items-center space-y-3">
              <div className="w-8 h-8 border-2 border-slate-200 border-t-blue-500 rounded-full animate-spin" />
              <p className="text-sm text-slate-500">Loading data...</p>
            </div>
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

// Enhanced Commission Trends Chart with Filters
function CommissionTrendsChart({ data, loading }: { data: any; loading: boolean }) {
  const [timeRange, setTimeRange] = useState('12m');
  const [compareMode, setCompareMode] = useState('none');
  const [viewType, setViewType] = useState('commission');

  const processedData = useMemo(() => {
    console.log('📈 Commission Trends - Raw Data:', data);
    
    if (!data || !Array.isArray(data) || data.length === 0) {
      console.log('⚠️ No data available for commission trends');
      return null;
    }
    
    const monthlyData = extractMonthlyData(data);
    console.log('📈 Monthly Data Processed:', monthlyData);
    
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    // Apply time range filter
    let filteredMonths = months;
    let filteredData = monthlyData;
    
    if (timeRange === '6m') {
      const currentMonth = new Date().getMonth();
      filteredMonths = months.slice(Math.max(0, currentMonth - 5), currentMonth + 1);
      filteredData = monthlyData.slice(Math.max(0, currentMonth - 5), currentMonth + 1);
    } else if (timeRange === '3m') {
      const currentMonth = new Date().getMonth();
      filteredMonths = months.slice(Math.max(0, currentMonth - 2), currentMonth + 1);
      filteredData = monthlyData.slice(Math.max(0, currentMonth - 2), currentMonth + 1);
    }

    const chartData = filteredData.map(d => viewType === 'commission' ? d.commission : d.count);
    console.log('📈 Chart Data Points:', chartData);
    console.log('📈 View Type:', viewType);
    console.log('📈 Filtered Data:', filteredData);
    
    const datasets = [
      {
        label: viewType === 'commission' ? 'Commission Earned' : 'Statement Count',
        data: chartData,
        borderColor: 'rgb(16, 185, 129)',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: 'rgb(16, 185, 129)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 6,
        pointHoverRadius: 8,
      }
    ];

    return {
      labels: filteredMonths,
      datasets
    };
  }, [data, timeRange, viewType]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(16, 185, 129, 1)',
        borderWidth: 1,
        padding: 12,
        callbacks: {
          label: (context: any) => {
            if (viewType === 'commission') {
              return `Commission: ${utilFormatCurrency(context.raw, true)}`;
            } else {
              return `Statements: ${Math.round(context.raw)}`;
            }
          }
        }
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#6B7280', font: { size: 12 } }
      },
      y: {
        grid: { color: 'rgba(241, 245, 249, 0.5)' },
        ticks: { 
          color: '#6B7280',
          callback: (value: any) => {
            if (viewType === 'commission') {
              return utilFormatCurrency(value, true);
            } else {
              return Math.round(value).toString();
            }
          }
        }
      }
    }
  };

  const filters = [
    <ChartFilter
      key="timeRange"
      title="Time Range"
      options={[
        { value: '3m', label: 'Last 3 Months' },
        { value: '6m', label: 'Last 6 Months' },
        { value: '12m', label: 'Last 12 Months' }
      ]}
      value={timeRange}
      onChange={setTimeRange}
      icon={Calendar}
    />,
    <ChartFilter
      key="viewType"
      title="View"
      options={[
        { value: 'commission', label: 'Commission ($)' },
        { value: 'statements', label: 'Statement Count' }
      ]}
      value={viewType}
      onChange={setViewType}
      icon={Eye}
    />
  ];

  const actions = [
    {
      icon: Download,
      title: 'Export Chart',
      onClick: () => console.log('Export chart')
    },
    {
      icon: ExternalLink,
      title: 'View Details',
      onClick: () => console.log('View details')
    }
  ];

  return (
    <ChartWrapper
      title="Commission Trends"
      subtitle="Monthly performance analysis"
      icon={LineChart}
      gradient="from-emerald-500 to-teal-600"
      filters={filters}
      actions={actions}
      loading={loading}
      className="col-span-2"
      infoText="This chart visualizes your commission earnings over time, helping you identify seasonal patterns, growth trends, and performance changes. Use the filters to switch between different time ranges and view either total commission amounts or statement counts."
    >
      <div className="h-80">
        {processedData ? (
          <Line data={processedData} options={chartOptions} />
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <LineChart className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-sm text-slate-500">No commission data available</p>
              <p className="text-xs text-slate-400 mt-1">Upload statements to see trends</p>
            </div>
          </div>
        )}
      </div>
    </ChartWrapper>
  );
}

// Enhanced Top Carriers Chart with Filters
function TopCarriersChart({ carriers, loading }: { carriers: any; loading: boolean }) {
  const [sortBy, setSortBy] = useState('commission');
  const [limit, setLimit] = useState('10');
  const [planFilter, setPlanFilter] = useState('');

  const processedData = useMemo(() => {
    console.log('🏢 Top Carriers - Raw Data:', carriers);
    console.log('🏢 First carrier sample:', carriers?.[0]);
    
    if (!carriers || !Array.isArray(carriers) || carriers.length === 0) {
      console.log('⚠️ No carriers data available');
      return null;
    }

    // Map carriers to standardized format
    let filteredCarriers = carriers.map((c: any) => {
      const standardized = {
        id: c.id,
        name: c.name || c.carrier_name || c.carriername || 'Unknown',
        // The endpoint returns total_commission from earned_commission/carriers
        commission: c.total_commission || c.totalCommission || c.totalcommission || 
                   c.commissiontotal || c.commission_total || 0,
        statementCount: c.statement_count || c.statementcount || c.statementCount || 
                       c.total_statements || 0,
        planType: c.plantype || c.plan_type || c.planType || null
      };
      console.log('🏢 Standardized carrier:', standardized);
      return standardized;
    });

    console.log('🏢 Standardized carriers:', filteredCarriers);
    
    // Apply plan filter if selected
    if (planFilter) {
      filteredCarriers = filteredCarriers.filter((c: any) => c.planType === planFilter);
    }

    // Sort carriers
    if (sortBy === 'commission') {
      filteredCarriers.sort((a: any, b: any) => b.commission - a.commission);
    } else if (sortBy === 'statements') {
      filteredCarriers.sort((a: any, b: any) => b.statementCount - a.statementCount);
    }

    // Limit results
    filteredCarriers = filteredCarriers.slice(0, parseInt(limit));
    
    console.log('🏢 Final carriers for chart:', filteredCarriers);

    return {
      labels: filteredCarriers.map((c: any) => c.name),
      datasets: [{
        label: 'Commission',
        data: filteredCarriers.map((c: any) => c.commission),
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)', 'rgba(16, 185, 129, 0.8)', 
          'rgba(139, 92, 246, 0.8)', 'rgba(245, 158, 11, 0.8)',
          'rgba(239, 68, 68, 0.8)', 'rgba(236, 72, 153, 0.8)',
          'rgba(34, 197, 94, 0.8)', 'rgba(168, 85, 247, 0.8)',
          'rgba(20, 184, 166, 0.8)', 'rgba(251, 146, 60, 0.8)'
        ],
        borderColor: [
          'rgba(59, 130, 246, 1)', 'rgba(16, 185, 129, 1)',
          'rgba(139, 92, 246, 1)', 'rgba(245, 158, 11, 1)',
          'rgba(239, 68, 68, 1)', 'rgba(236, 72, 153, 1)',
          'rgba(34, 197, 94, 1)', 'rgba(168, 85, 247, 1)',
          'rgba(20, 184, 166, 1)', 'rgba(251, 146, 60, 1)'
        ],
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }]
    };
  }, [carriers, sortBy, limit, planFilter]);

  const chartOptions = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        callbacks: {
          label: (context: any) => `Commission: ${utilFormatCurrency(context.raw, true)}`
        }
      }
    },
    scales: {
      x: {
        grid: { color: 'rgba(241, 245, 249, 0.5)' },
        ticks: { 
          color: '#6B7280',
          callback: (value: any) => utilFormatCurrency(value, true)
        }
      },
      y: {
        grid: { display: false },
        ticks: { color: '#6B7280', font: { size: 11 } }
      }
    }
  };

  const filters = [
    <ChartFilter
      key="sortBy"
      options={[
        { value: 'commission', label: 'By Commission' },
        { value: 'statements', label: 'By Statements' }
      ]}
      value={sortBy}
      onChange={setSortBy}
      icon={SlidersHorizontal}
      placeholder="Sort by"
    />,
    <ChartFilter
      key="limit"
      options={[
        { value: '5', label: 'Top 5' },
        { value: '10', label: 'Top 10' },
        { value: '15', label: 'Top 15' }
      ]}
      value={limit}
      onChange={setLimit}
      icon={Award}
      placeholder="Show"
    />
  ];

  const actions = [
    {
      icon: Download,
      title: 'Export Data',
      onClick: () => console.log('Export carriers data')
    }
  ];

  return (
    <ChartWrapper
      title="Top Performing Carriers"
      subtitle="By total commission volume"
      icon={Award}
      gradient="from-blue-500 to-indigo-600"
      filters={filters}
      actions={actions}
      loading={loading}
      infoText="This chart ranks your carriers by performance, showing which ones generate the most commission or have the highest statement volume. Use this to identify your most valuable partnerships and optimize your focus on high-performing carriers."
    >
      <div className="h-80">
        {processedData ? (
          <Bar data={processedData} options={chartOptions} />
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-sm text-slate-500">No carrier data available</p>
              <p className="text-xs text-slate-400 mt-1">Add carriers to see performance</p>
            </div>
          </div>
        )}
      </div>
    </ChartWrapper>
  );
}

// Enhanced Plan Distribution Chart with Filters
function PlanDistributionChart({ data }: { data: any }) {
  const [metric, setMetric] = useState('count');
  const [minValue, setMinValue] = useState('0');

  const processedData = useMemo(() => {
    console.log('📊 Plan Distribution - Raw Data:', data);
    
    if (!data || !Array.isArray(data) || data.length === 0) {
      console.log('⚠️ No data available for plan distribution');
      return null;
    }

    const planData = data.reduce((acc: any, item: any) => {
      const planType = item.plantype || item.plan_type || 'Other';
      if (!acc[planType]) {
        acc[planType] = { count: 0, commission: 0 };
      }
      acc[planType].count += 1;
      acc[planType].commission += item.commissionearned || item.commission_earned || 0;
      return acc;
    }, {} as Record<string, { count: number; commission: number }>);
    
    console.log('📊 Plan Data Aggregated:', planData);

    // Filter by minimum value
    const minVal = parseInt(minValue);
    const filteredData = Object.entries(planData)
      .filter(([_, values]: [string, any]) => 
        metric === 'count' ? values.count >= minVal : values.commission >= minVal
      );

    return {
      labels: filteredData.map(([planType]) => planType),
      datasets: [{
        data: filteredData.map(([_, values]: [string, any]) => 
          metric === 'count' ? values.count : values.commission
        ),
        backgroundColor: [
          'rgba(99, 102, 241, 0.8)', 'rgba(16, 185, 129, 0.8)',
          'rgba(245, 158, 11, 0.8)', 'rgba(239, 68, 68, 0.8)',
          'rgba(168, 85, 247, 0.8)', 'rgba(236, 72, 153, 0.8)'
        ],
        borderColor: [
          'rgba(99, 102, 241, 1)', 'rgba(16, 185, 129, 1)',
          'rgba(245, 158, 11, 1)', 'rgba(239, 68, 68, 1)',
          'rgba(168, 85, 247, 1)', 'rgba(236, 72, 153, 1)'
        ],
        borderWidth: 2,
      }]
    };
  }, [data, metric, minValue]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: { padding: 15, usePointStyle: true, font: { size: 12 } }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        callbacks: {
          label: (context: any) => 
            metric === 'count'
              ? `${context.label}: ${context.raw} statements`
              : `${context.label}: ${utilFormatCurrency(context.raw, true)}`
        }
      }
    }
  };

  const filters = [
    <ChartFilter
      key="metric"
      options={[
        { value: 'count', label: 'Statement Count' },
        { value: 'commission', label: 'Commission Value' }
      ]}
      value={metric}
      onChange={setMetric}
      icon={PieChart}
      placeholder="View by"
    />,
    <ChartFilter
      key="minValue"
      options={[
        { value: '0', label: 'Show All' },
        { value: '5', label: 'Min 5+' },
        { value: '10', label: 'Min 10+' }
      ]}
      value={minValue}
      onChange={setMinValue}
      icon={Filter}
      placeholder="Filter"
    />
  ];

  return (
    <ChartWrapper
      title="Plan Distribution"
      subtitle="By plan type"
      icon={PieChart}
      gradient="from-indigo-500 to-purple-600"
      filters={filters}
      actions={[]}
      loading={!data}
      infoText="This doughnut chart breaks down your business by plan type (e.g., Medicare, ACA, Life Insurance), showing how your portfolio is distributed. Use the filters to view by either statement count or commission value to understand which plan types drive your revenue."
    >
      <div className="h-64 flex items-center justify-center">
        {processedData ? (
          <Doughnut data={processedData} options={chartOptions} />
        ) : (
          <div className="text-center">
            <PieChart className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-sm text-slate-500">No plan data available</p>
            <p className="text-xs text-slate-400 mt-1">Upload statements to see distribution</p>
          </div>
        )}
      </div>
    </ChartWrapper>
  );
}

// Main Component with 90% Width
export default function PremiumAnalyticsTab({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const currentYear = new Date().getFullYear();
  const [selectedYear, setSelectedYear] = useState(currentYear);

  // Data hooks
  const { stats: currentStats, loading: currentStatsLoading } = useEarnedCommissionStats(selectedYear);
  const { stats: dashboardStats, loading: dashboardLoading } = useDashboardStats(true);
  const { data: currentYearData, loading: currentDataLoading } = useAllCommissionData(selectedYear);
  const { carriers, loading: carriersLoading } = useCarriersWithCommission();
  const { years: availableYears, loading: yearsLoading } = useAvailableYears();
  const { data: pieChartData, loading: pieChartLoading } = useCarrierPieChartData(selectedYear);

  const loading = currentStatsLoading || dashboardLoading || currentDataLoading;

  // Hero metrics calculation with proper backend data integration
  const heroMetrics = useMemo(() => {
    console.log('📊 Current Stats:', currentStats);
    console.log('📊 Dashboard Stats:', dashboardStats);
    console.log('📊 Current Year Data:', currentYearData);
    
    // Calculate total commission from current year data if stats not available
    let totalCommission = 0;
    if (currentStats?.totalcommission !== undefined) {
      totalCommission = currentStats.totalcommission;
    } else if (currentYearData && Array.isArray(currentYearData)) {
      totalCommission = currentYearData.reduce((sum, item) => {
        return sum + (item.commissionearned || item.commission_earned || 0);
      }, 0);
    }

    const totalCarriers = dashboardStats?.total_carriers || carriers?.length || 0;
    const totalStatements = dashboardStats?.total_statements || currentYearData?.length || 0;
    const approvedStatements = dashboardStats?.approved_statements || 0;
    const rejectedStatements = dashboardStats?.rejected_statements || 0;
    const totalProcessed = approvedStatements + rejectedStatements;
    const successRate = totalProcessed > 0 ? (approvedStatements / totalProcessed) * 100 : 0;

    return {
      totalCommission,
      totalCarriers,
      totalStatements,
      successRate
    };
  }, [currentStats, dashboardStats, currentYearData, carriers]);

  return (
    <div className="min-h-screen">
      
      {/* Full Width Content - 90% of screen width */}
      <div className="w-full px-4 md:px-6 lg:px-8 py-6 md:py-8" style={{ maxWidth: '90vw', margin: '0 auto' }}>
        
        {/* Year Selector - Top Right */}
        <div className="flex justify-end mb-6">
          {!yearsLoading && availableYears && availableYears.length > 0 && (
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-sm font-medium text-slate-700 dark:text-white hover:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            >
              {availableYears.map((year: number) => (
                <option key={year} value={year} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">{year}</option>
              ))}
            </select>
          )}
        </div>
        
        {/* Hero Metrics - Full Width */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="group relative overflow-hidden bg-white dark:bg-slate-800 rounded-2xl border border-emerald-200 dark:border-emerald-800 p-6 shadow-lg shadow-emerald-500/20 hover:scale-105 transition-all duration-300"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500 to-teal-600 opacity-0 group-hover:opacity-5 transition-opacity" />
            <div className="relative">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                  <DollarSign className="w-6 h-6 text-white" />
                </div>
                <div className="flex items-center space-x-1 text-sm">
                  <ArrowUpRight className="w-4 h-4 text-emerald-500" />
                  <span className="font-semibold text-emerald-600">18.2%</span>
                </div>
              </div>
              <div className="text-3xl font-bold text-slate-900 dark:text-white mb-1">
                {utilFormatCurrency(heroMetrics.totalCommission, true)}
              </div>
              <div className="text-sm font-medium text-slate-600">Total Commission</div>
              <div className="text-xs text-slate-500 mt-1">vs last year</div>
            </div>
          </motion.div>

          {/* Additional hero metrics... */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="group relative overflow-hidden bg-white dark:bg-slate-800 rounded-2xl border border-blue-200 dark:border-blue-800 p-6 shadow-sm hover:scale-105 transition-all duration-300"
          >
            <div className="relative">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg">
                  <Building2 className="w-6 h-6 text-white" />
                </div>
                <div className="text-sm text-slate-600">+8.3%</div>
              </div>
              <div className="text-3xl font-bold text-slate-900 dark:text-white mb-1">
                {heroMetrics.totalCarriers}
              </div>
              <div className="text-sm font-medium text-slate-600">Active Carriers</div>
              <div className="text-xs text-slate-500 mt-1">this year</div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="group relative overflow-hidden bg-white dark:bg-slate-800 rounded-2xl border border-purple-200 dark:border-purple-800 p-6 shadow-sm hover:scale-105 transition-all duration-300"
          >
            <div className="relative">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-r from-purple-500 to-violet-600 flex items-center justify-center shadow-lg">
                  <BarChart3 className="w-6 h-6 text-white" />
                </div>
                <div className="text-sm text-slate-600">+12.8%</div>
              </div>
              <div className="text-3xl font-bold text-slate-900 dark:text-white mb-1">
                {heroMetrics.totalStatements}
              </div>
              <div className="text-sm font-medium text-slate-600">Total Statements</div>
              <div className="text-xs text-slate-500 mt-1">processed</div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="group relative overflow-hidden bg-white dark:bg-slate-800 rounded-2xl border border-green-200 dark:border-green-800 p-6 shadow-sm hover:scale-105 transition-all duration-300"
          >
            <div className="relative">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-r from-green-500 to-emerald-600 flex items-center justify-center shadow-lg">
                  <CheckCircle className="w-6 h-6 text-white" />
                </div>
                <div className="text-sm text-slate-600">+2.1%</div>
              </div>
              <div className="text-3xl font-bold text-slate-900 dark:text-white mb-1">
                {heroMetrics.successRate.toFixed(1)}%
              </div>
              <div className="text-sm font-medium text-slate-600">Success Rate</div>
              <div className="text-xs text-slate-500 mt-1">processing quality</div>
            </div>
          </motion.div>
        </div>

        {/* Main Charts Grid - Full Width with Individual Filters */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          {/* Commission Trends - Takes 2 columns with individual filters */}
          <CommissionTrendsChart 
            data={currentYearData} 
            loading={currentDataLoading} 
          />
          
          {/* Top Carriers - Takes 1 column with individual filters */}
          <TopCarriersChart 
            carriers={carriers} 
            loading={carriersLoading} 
          />
        </div>

        {/* Premium Carrier Distribution Pie Chart - Full Width */}
        <div className="grid grid-cols-1 lg:grid-cols-1 gap-8 mb-8">
          <PremiumCarrierPieChart 
            data={pieChartData}
            loading={pieChartLoading}
            year={selectedYear}
          />
        </div>

        {/* Secondary Charts - Full Width */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <PlanDistributionChart data={currentYearData} />
          
          {/* Key Insights Card */}
          <div className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-2xl border border-blue-200 dark:border-blue-800 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Target className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Key Insights</h3>
              <InfoTooltip content="This section highlights the most important insights from your data, including top performer metrics and year-over-year growth trends to help you quickly understand your business performance." />
            </div>
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-emerald-500 rounded-full mt-2" />
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">Top Performance</p>
                  <p className="text-xs text-slate-600 dark:text-slate-400">Your leading carrier generates 68% of total commission</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-2" />
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">Growth Trend</p>
                  <p className="text-xs text-slate-600 dark:text-slate-400">18.2% increase compared to last year</p>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm p-6">
            <div className="flex items-center space-x-2 mb-4">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Quick Actions</h3>
              <InfoTooltip content="Quick access links to commonly used features like viewing detailed reports and managing your carriers. Click any action to navigate directly to that section." />
            </div>
            <div className="space-y-3">
              <button 
                onClick={() => onNavigate?.('dashboard')}
                className="w-full flex items-center justify-between p-3 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:hover:bg-blue-900/30 rounded-lg transition-colors text-left"
              >
                <div className="flex items-center space-x-3">
                  <BarChart3 className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium">View Detailed Report</span>
                </div>
                <ExternalLink className="w-4 h-4 text-slate-400" />
              </button>
              <button 
                onClick={() => onNavigate?.('carriers')}
                className="w-full flex items-center justify-between p-3 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:hover:bg-emerald-900/30 rounded-lg transition-colors text-left"
              >
                <div className="flex items-center space-x-3">
                  <Building2 className="w-4 h-4 text-emerald-600" />
                  <span className="text-sm font-medium">Manage Carriers</span>
                </div>
                <ExternalLink className="w-4 h-4 text-slate-400" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
