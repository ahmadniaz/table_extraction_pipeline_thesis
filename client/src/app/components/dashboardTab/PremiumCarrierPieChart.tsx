'use client';

import React, { useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Building2, DollarSign, FileText, Search, HelpCircle } from 'lucide-react';
import { formatCurrency, formatPercentage } from '../../utils/analyticsUtils';

ChartJS.register(ArcElement, Tooltip, Legend);

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

interface CarrierData {
  id: string;
  name: string;
  total_commission?: number;
  totalCommission?: number;
  statement_count?: number;
  statementCount?: number;
  percentage?: number;
}

interface PremiumCarrierPieChartProps {
  data: CarrierData[];
  loading: boolean;
  year?: number;
}

const PREMIUM_COLORS = [
  'rgba(59, 130, 246, 0.8)',   // Blue
  'rgba(16, 185, 129, 0.8)',   // Green
  'rgba(245, 158, 11, 0.8)',   // Amber
  'rgba(239, 68, 68, 0.8)',    // Red
  'rgba(139, 92, 246, 0.8)',   // Purple
  'rgba(236, 72, 153, 0.8)',   // Pink
  'rgba(14, 165, 233, 0.8)',   // Sky
  'rgba(34, 197, 94, 0.8)',    // Emerald
  'rgba(251, 146, 60, 0.8)',   // Orange
  'rgba(168, 85, 247, 0.8)',   // Violet
];

const PREMIUM_HOVER_COLORS = [
  'rgba(59, 130, 246, 1)',
  'rgba(16, 185, 129, 1)',
  'rgba(245, 158, 11, 1)',
  'rgba(239, 68, 68, 1)',
  'rgba(139, 92, 246, 1)',
  'rgba(236, 72, 153, 1)',
  'rgba(14, 165, 233, 1)',
  'rgba(34, 197, 94, 1)',
  'rgba(251, 146, 60, 1)',
  'rgba(168, 85, 247, 1)',
];

export default function PremiumCarrierPieChart({ data, loading, year }: PremiumCarrierPieChartProps) {
  const [selectedCarrier, setSelectedCarrier] = useState<CarrierData | null>(null);
  const [hoveredCarrier, setHoveredCarrier] = useState<CarrierData | null>(null);
  const [filterType, setFilterType] = useState<'commission' | 'statements'>('commission');
  const [searchTerm, setSearchTerm] = useState('');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const chartRef = useRef<any>(null);

  // Filter and process data
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    const filtered = data.filter(carrier => {
      const carrierName = carrier.name || '';
      const commission = carrier.total_commission || carrier.totalCommission || 0;
      return carrierName.toLowerCase().includes(searchTerm.toLowerCase()) && commission > 0;
    });

    // Calculate percentages
    const total = filterType === 'commission' 
      ? filtered.reduce((sum, carrier) => sum + (carrier.total_commission || carrier.totalCommission || 0), 0)
      : filtered.reduce((sum, carrier) => sum + (carrier.statement_count || carrier.statementCount || 0), 0);

    return filtered.map(carrier => ({
      ...carrier,
      percentage: filterType === 'commission' 
        ? ((carrier.total_commission || carrier.totalCommission || 0) / total) * 100
        : ((carrier.statement_count || carrier.statementCount || 0) / total) * 100
    })).sort((a, b) => (b.percentage || 0) - (a.percentage || 0));
  }, [data, searchTerm, filterType]);

  // Chart configuration
  const chartData = useMemo(() => ({
    labels: processedData.map(carrier => carrier.name),
    datasets: [{
      data: processedData.map(carrier => 
        filterType === 'commission' 
          ? (carrier.total_commission || carrier.totalCommission || 0)
          : (carrier.statement_count || carrier.statementCount || 0)
      ),
      backgroundColor: PREMIUM_COLORS,
      hoverBackgroundColor: PREMIUM_HOVER_COLORS,
      borderWidth: 2,
      borderColor: '#ffffff',
      hoverBorderWidth: 4,
      hoverBorderColor: '#ffffff',
    }]
  }), [processedData, filterType]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false, // Custom legend
      },
      tooltip: {
        enabled: false, // Disable default tooltip, we show custom info panel
      },
    },
    animation: {
      animateRotate: true,
      animateScale: true,
      duration: 1000,
    },
    elements: {
      arc: {
        borderWidth: 2,
        hoverBorderWidth: 4,
        hoverOffset: 15,
      }
    },
    onHover: (event: any, elements: any[], chart: any) => {
      // Change cursor style
      const canvas = chart.canvas;
      if (canvas) {
        canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default';
      }
      
      if (elements.length > 0) {
        const index = elements[0].index;
        setHoveredIndex(index);
        setHoveredCarrier(processedData[index]);
      } else {
        // Only clear hover if not hovering over legend item
        if (!selectedCarrier) {
          setHoveredIndex(null);
          setHoveredCarrier(null);
        }
      }
    },
    onClick: (event: any, elements: any[]) => {
      if (elements.length > 0) {
        const index = elements[0].index;
        setSelectedCarrier(processedData[index]);
      }
    },
  }), [processedData, selectedCarrier]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-gray-500">
        <Building2 className="w-16 h-16 mb-4 opacity-50" />
        <p className="text-lg font-medium mb-2">No Commission Data</p>
        <p className="text-sm">Upload statements to see carrier distribution</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg border border-gray-100 dark:border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-100 dark:border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Building2 className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">Commission Distribution</h3>
                <InfoTooltip content="This interactive pie chart shows how your commission is distributed across all carriers. Hover over any segment to see detailed information, or click to pin a carrier's details. The chart can be filtered to show either commission amounts or statement counts, helping you understand which carriers contribute most to your business." />
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                By carrier {year ? `for ${year}` : '(all time)'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setFilterType('commission')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterType === 'commission'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                  : 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-400'
              }`}
            >
              <DollarSign className="w-4 h-4 mr-2 inline" />
              Commission
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setFilterType('statements')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterType === 'statements'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
                  : 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-400'
              }`}
            >
              <FileText className="w-4 h-4 mr-2 inline" />
              Statements
            </motion.button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search carriers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
          />
        </div>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chart */}
          <div className="lg:col-span-2">
            <div className="relative h-80 flex items-center justify-center">
              <div className="w-full h-full relative">
                {/* Add shadow effect for hovered slice */}
                {hoveredIndex !== null && (
                  <div 
                    className="absolute inset-0 pointer-events-none"
                    style={{
                      background: `radial-gradient(circle at center, ${PREMIUM_COLORS[hoveredIndex % PREMIUM_COLORS.length].replace('0.8', '0.1')} 0%, transparent 70%)`,
                      filter: 'blur(20px)',
                      zIndex: 0
                    }}
                  />
                )}
                <Pie ref={chartRef} data={chartData} options={{
                      ...chartOptions,
                      layout: {
                        padding: {
                          top: 10,
                          bottom: 10,
                          left: 10,
                          right: 10,
                        }
                      },
                      maintainAspectRatio: false,
                    }}/>
              </div>
            </div>
          </div>

          {/* Carrier List */}
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {processedData.map((carrier, index) => {
              const commission = carrier.total_commission || carrier.totalCommission || 0;
              const statementCount = carrier.statement_count || carrier.statementCount || 0;
              
              const handleMouseEnter = () => {
                setHoveredIndex(index);
                setHoveredCarrier(carrier);
                
                // Trigger chart hover effect
                if (chartRef.current) {
                  const chart = chartRef.current;
                  const activeElements = [{
                    datasetIndex: 0,
                    index: index
                  }];
                  chart.setActiveElements(activeElements);
                  chart.update();
                }
              };
              
              const handleMouseLeave = () => {
                // Don't clear hover if item is selected
                if (selectedCarrier?.id !== carrier.id) {
                  setHoveredIndex(null);
                  setHoveredCarrier(null);
                  
                  // Clear chart hover effect
                  if (chartRef.current) {
                    const chart = chartRef.current;
                    chart.setActiveElements([]);
                    chart.update();
                  }
                }
              };
              
              return (
                <motion.div
                  key={carrier.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`p-3 rounded-lg border transition-all cursor-pointer ${
                    hoveredIndex === index || selectedCarrier?.id === carrier.id
                      ? 'border-blue-200 bg-blue-50 shadow-md dark:border-blue-800 dark:bg-blue-900/20'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 dark:border-slate-700 dark:hover:border-slate-600 dark:hover:bg-slate-700/50'
                  }`}
                  onClick={() => setSelectedCarrier(carrier)}
                  onMouseEnter={handleMouseEnter}
                  onMouseLeave={handleMouseLeave}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <div
                        className="w-4 h-4 rounded-full flex-shrink-0"
                        style={{ backgroundColor: PREMIUM_COLORS[index % PREMIUM_COLORS.length] }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 dark:text-white truncate">
                          {carrier.name}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {statementCount} statements
                        </p>
                      </div>
                    </div>
                    <div className="text-right ml-3 flex-shrink-0">
                      <p className="font-bold text-gray-900 dark:text-white">
                        {formatPercentage(carrier.percentage || 0)}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {filterType === 'commission' 
                          ? formatCurrency(commission, true)
                          : statementCount
                        }
                      </p>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Carrier Details - Shows on hover or when selected */}
        <AnimatePresence>
          {(hoveredCarrier || selectedCarrier) && (() => {
            const displayCarrier = selectedCarrier || hoveredCarrier;
            const carrierIndex = processedData.findIndex(c => c.id === displayCarrier?.id);
            const carrierColor = PREMIUM_COLORS[carrierIndex % PREMIUM_COLORS.length];
            const carrierHoverColor = PREMIUM_HOVER_COLORS[carrierIndex % PREMIUM_HOVER_COLORS.length];
            
            // Extract RGB values from rgba string
            const rgbMatch = carrierColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
            const r = rgbMatch ? rgbMatch[1] : '59';
            const g = rgbMatch ? rgbMatch[2] : '130';
            const b = rgbMatch ? rgbMatch[3] : '246';
            
            return (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="mt-6 p-4 rounded-xl border"
                style={{
                  background: selectedCarrier 
                    ? `linear-gradient(135deg, rgba(${r}, ${g}, ${b}, 0.15) 0%, rgba(${r}, ${g}, ${b}, 0.05) 100%)`
                    : `linear-gradient(135deg, rgba(${r}, ${g}, ${b}, 0.08) 0%, rgba(${r}, ${g}, ${b}, 0.03) 100%)`,
                  borderColor: selectedCarrier 
                    ? carrierHoverColor.replace('1)', '0.3)')
                    : carrierColor.replace('0.8', '0.2')
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: carrierHoverColor }}
                    />
                    <h4 
                      className="text-lg font-bold"
                      style={{ 
                        color: selectedCarrier 
                          ? carrierHoverColor.replace('1)', '1)')
                          : `rgba(${r}, ${g}, ${b}, 0.9)`
                      }}
                    >
                      {displayCarrier?.name}
                    </h4>
                    {!selectedCarrier && hoveredCarrier && (
                      <span 
                        className="text-xs px-2 py-1 rounded-full font-medium"
                        style={{ 
                          backgroundColor: carrierColor.replace('0.8', '0.2'),
                          color: carrierHoverColor
                        }}
                      >
                        Hover preview
                      </span>
                    )}
                  </div>
                  {selectedCarrier && (
                    <button
                      onClick={() => setSelectedCarrier(null)}
                      className="text-xl font-bold hover:opacity-70 transition-opacity"
                      style={{ color: carrierHoverColor }}
                    >
                      ×
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p 
                      className="text-2xl font-bold"
                      style={{ color: carrierHoverColor }}
                    >
                      {formatCurrency((displayCarrier?.total_commission || displayCarrier?.totalCommission || 0), true)}
                    </p>
                    <p 
                      className="text-sm"
                      style={{ color: carrierColor.replace('0.8', '0.7') }}
                    >
                      Total Commission
                    </p>
                  </div>
                  <div className="text-center">
                    <p 
                      className="text-2xl font-bold"
                      style={{ color: carrierHoverColor }}
                    >
                      {displayCarrier?.statement_count || displayCarrier?.statementCount || 0}
                    </p>
                    <p 
                      className="text-sm"
                      style={{ color: carrierColor.replace('0.8', '0.7') }}
                    >
                      Statements
                    </p>
                  </div>
                  <div className="text-center">
                    <p 
                      className="text-2xl font-bold"
                      style={{ color: carrierHoverColor }}
                    >
                      {formatPercentage(displayCarrier?.percentage || 0)}
                    </p>
                    <p 
                      className="text-sm"
                      style={{ color: carrierColor.replace('0.8', '0.7') }}
                    >
                      Share
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })()}
        </AnimatePresence>
      </div>
    </div>
  );
}

