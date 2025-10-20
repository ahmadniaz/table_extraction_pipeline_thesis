/**
 * Analytics Utilities
 * Data processing, calculations, and transformations for analytics dashboard
 */

interface CommissionData {
  id: string;
  carrier_name?: string;
  client_name: string;
  invoice_total: number;
  commission_earned: number;
  statement_count: number;
  statement_date?: string;
  statement_month?: number;
  statement_year?: number;
  monthly_breakdown?: {
    jan: number; feb: number; mar: number; apr: number;
    may: number; jun: number; jul: number; aug: number;
    sep: number; oct: number; nov: number; dec: number;
  };
}

interface CarrierPerformance {
  id: string;
  name: string;
  totalCommission: number;
  totalInvoice: number;
  statementCount: number;
  averageCommission: number;
  commissionRate: number;
  growth?: number;
  trend?: 'up' | 'down' | 'stable';
}

/**
 * Calculate commission growth between two periods
 */
export function calculateCommissionGrowth(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0;
  return ((current - previous) / previous) * 100;
}

/**
 * Calculate average commission per statement
 */
export function calculateAverageCommission(totalCommission: number, statementCount: number): number {
  return statementCount > 0 ? totalCommission / statementCount : 0;
}

/**
 * Calculate commission rate (commission / invoice)
 */
export function calculateCommissionRate(commission: number, invoice: number): number {
  return invoice > 0 ? (commission / invoice) * 100 : 0;
}

/**
 * Identify top performing carriers
 */
export function identifyTopPerformingCarriers(
  data: CommissionData[], 
  limit: number = 10
): CarrierPerformance[] {
  // Group by carrier
  const carrierMap = new Map<string, {
    commission: number;
    invoice: number;
    count: number;
  }>();

  data.forEach(item => {
    const carrier = item.carrier_name || 'Unknown';
    const existing = carrierMap.get(carrier) || { commission: 0, invoice: 0, count: 0 };
    
    carrierMap.set(carrier, {
      commission: existing.commission + item.commission_earned,
      invoice: existing.invoice + item.invoice_total,
      count: existing.count + item.statement_count
    });
  });

  // Convert to array and calculate metrics
  const carriers: CarrierPerformance[] = Array.from(carrierMap.entries()).map(([name, stats]) => ({
    id: name.toLowerCase().replace(/\s+/g, '-'),
    name,
    totalCommission: stats.commission,
    totalInvoice: stats.invoice,
    statementCount: stats.count,
    averageCommission: stats.count > 0 ? stats.commission / stats.count : 0,
    commissionRate: stats.invoice > 0 ? (stats.commission / stats.invoice) * 100 : 0,
    trend: 'stable' as const
  }));

  // Sort by total commission and return top performers
  return carriers.sort((a, b) => b.totalCommission - a.totalCommission).slice(0, limit);
}

/**
 * Extract monthly commission data for charting
 */
export function extractMonthlyData(data: CommissionData[]): {
  month: string;
  commission: number;
  invoice: number;
  count: number;
}[] {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthlyData = Array(12).fill(null).map((_, i) => ({
    month: months[i],
    commission: 0,
    invoice: 0,
    count: 0
  }));

  data.forEach(item => {
    if (item.monthly_breakdown) {
      const breakdown = item.monthly_breakdown;
      const keys: (keyof typeof breakdown)[] = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
      
      keys.forEach((key, index) => {
        if (breakdown[key] && breakdown[key] > 0) {
          monthlyData[index].commission += breakdown[key] || 0;
          monthlyData[index].count += 1; // Increment count for each month that has data
        }
      });
    } else if (item.statement_month !== undefined || (item as any).statementmonth !== undefined) {
      const monthIndex = (item.statement_month || (item as any).statementmonth || 1) - 1;
      if (monthIndex >= 0 && monthIndex < 12) {
        monthlyData[monthIndex].commission += item.commission_earned || (item as any).commissionearned || 0;
        monthlyData[monthIndex].invoice += item.invoice_total || (item as any).invoicetotal || 0;
        // Count each statement as 1 entry
        monthlyData[monthIndex].count += 1;
      }
    } else if ((item as any).statementdate) {
      // Handle date string format
      const dateStr = (item as any).statementdate;
      const date = new Date(dateStr);
      if (!isNaN(date.getTime())) {
        const monthIndex = date.getMonth();
        monthlyData[monthIndex].commission += (item as any).commissionearned || item.commission_earned || 0;
        monthlyData[monthIndex].invoice += (item as any).invoicetotal || item.invoice_total || 0;
        monthlyData[monthIndex].count += 1;
      }
    }
  });

  return monthlyData;
}

/**
 * Detect seasonal patterns
 */
export function detectSeasonalPatterns(monthlyData: { month: string; commission: number }[]): {
  peakMonth: string;
  lowestMonth: string;
  seasonality: 'high' | 'medium' | 'low';
  variance: number;
} {
  const commissions = monthlyData.map(d => d.commission).filter(c => c > 0);
  
  if (commissions.length === 0) {
    return {
      peakMonth: 'N/A',
      lowestMonth: 'N/A',
      seasonality: 'low',
      variance: 0
    };
  }

  const maxCommission = Math.max(...commissions);
  const minCommission = Math.min(...commissions);
  const avgCommission = commissions.reduce((a, b) => a + b, 0) / commissions.length;
  
  const peakMonth = monthlyData.find(d => d.commission === maxCommission)?.month || 'N/A';
  const lowestMonth = monthlyData.find(d => d.commission === minCommission)?.month || 'N/A';
  
  const variance = avgCommission > 0 ? ((maxCommission - minCommission) / avgCommission) * 100 : 0;
  
  let seasonality: 'high' | 'medium' | 'low' = 'low';
  if (variance > 50) seasonality = 'high';
  else if (variance > 25) seasonality = 'medium';
  
  return { peakMonth, lowestMonth, seasonality, variance };
}

/**
 * Calculate portfolio diversification
 */
export function calculatePortfolioDiversification(carriers: CarrierPerformance[]): {
  topCarrierConcentration: number;
  top3Concentration: number;
  diversificationScore: number;
  risk: 'high' | 'medium' | 'low';
} {
  const totalCommission = carriers.reduce((sum, c) => sum + c.totalCommission, 0);
  
  if (totalCommission === 0 || carriers.length === 0) {
    return {
      topCarrierConcentration: 0,
      top3Concentration: 0,
      diversificationScore: 0,
      risk: 'high'
    };
  }

  const topCarrierCommission = carriers[0]?.totalCommission || 0;
  const top3Commission = carriers.slice(0, 3).reduce((sum, c) => sum + c.totalCommission, 0);
  
  const topCarrierConcentration = (topCarrierCommission / totalCommission) * 100;
  const top3Concentration = (top3Commission / totalCommission) * 100;
  
  // Higher score = better diversification
  const diversificationScore = 100 - top3Concentration;
  
  let risk: 'high' | 'medium' | 'low' = 'low';
  if (topCarrierConcentration > 50) risk = 'high';
  else if (topCarrierConcentration > 30) risk = 'medium';
  
  return {
    topCarrierConcentration,
    top3Concentration,
    diversificationScore,
    risk
  };
}

/**
 * Generate carrier growth comparison
 */
export function compareCarrierGrowth(
  currentYearData: CommissionData[],
  previousYearData: CommissionData[]
): Map<string, { current: number; previous: number; growth: number }> {
  const growthMap = new Map<string, { current: number; previous: number; growth: number }>();
  
  // Calculate current year totals
  currentYearData.forEach(item => {
    const carrier = item.carrier_name || 'Unknown';
    const existing = growthMap.get(carrier) || { current: 0, previous: 0, growth: 0 };
    growthMap.set(carrier, {
      ...existing,
      current: existing.current + item.commission_earned
    });
  });
  
  // Calculate previous year totals
  previousYearData.forEach(item => {
    const carrier = item.carrier_name || 'Unknown';
    const existing = growthMap.get(carrier) || { current: 0, previous: 0, growth: 0 };
    growthMap.set(carrier, {
      ...existing,
      previous: existing.previous + item.commission_earned
    });
  });
  
  // Calculate growth percentage
  growthMap.forEach((value, key) => {
    value.growth = calculateCommissionGrowth(value.current, value.previous);
  });
  
  return growthMap;
}

/**
 * Identify opportunities from data patterns
 */
export function identifyOpportunities(
  carriers: CarrierPerformance[],
  seasonalData: ReturnType<typeof detectSeasonalPatterns>
): string[] {
  const opportunities: string[] = [];
  
  // High-value carrier opportunity
  const avgRate = carriers.reduce((sum, c) => sum + c.commissionRate, 0) / carriers.length;
  const highPerformers = carriers.filter(c => c.commissionRate > avgRate * 1.2);
  
  if (highPerformers.length > 0) {
    const bestCarrier = highPerformers[0];
    opportunities.push(
      `${bestCarrier.name} shows ${bestCarrier.commissionRate.toFixed(1)}% commission rate, ${((bestCarrier.commissionRate / avgRate - 1) * 100).toFixed(0)}% above average. Consider expanding this relationship.`
    );
  }
  
  // Seasonal opportunity
  if (seasonalData.seasonality !== 'low') {
    opportunities.push(
      `Historical data shows ${seasonalData.peakMonth} as your peak month. Plan capacity and resources accordingly.`
    );
  }
  
  // Diversification opportunity
  if (carriers.length > 5) {
    const bottomPerformers = carriers.slice(-3);
    const totalBottom = bottomPerformers.reduce((sum, c) => sum + c.totalCommission, 0);
    const totalAll = carriers.reduce((sum, c) => sum + c.totalCommission, 0);
    
    if (totalBottom / totalAll < 0.05) {
      opportunities.push(
        `Bottom 3 carriers contribute only ${((totalBottom / totalAll) * 100).toFixed(1)}% of revenue. Consider reviewing these relationships.`
      );
    }
  }
  
  return opportunities;
}

/**
 * Format currency for display
 */
export function formatCurrency(amount: number, compact: boolean = false): string {
  if (compact) {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}K`;
    }
  }
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
}

/**
 * Format percentage
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Calculate trend direction
 */
export function calculateTrend(values: number[]): 'up' | 'down' | 'stable' {
  if (values.length < 2) return 'stable';
  
  const recentAvg = values.slice(-3).reduce((a, b) => a + b, 0) / 3;
  const olderAvg = values.slice(0, 3).reduce((a, b) => a + b, 0) / 3;
  
  const change = ((recentAvg - olderAvg) / olderAvg) * 100;
  
  if (change > 5) return 'up';
  if (change < -5) return 'down';
  return 'stable';
}

/**
 * Generate year comparison data
 */
export function generateYearComparison(
  currentYear: number,
  currentData: CommissionData[],
  previousData: CommissionData[]
): {
  year: number;
  current: number;
  previous: number;
  growth: number;
  growthRate: number;
} {
  const currentTotal = currentData.reduce((sum, d) => sum + d.commission_earned, 0);
  const previousTotal = previousData.reduce((sum, d) => sum + d.commission_earned, 0);
  const growth = currentTotal - previousTotal;
  const growthRate = calculateCommissionGrowth(currentTotal, previousTotal);
  
  return {
    year: currentYear,
    current: currentTotal,
    previous: previousTotal,
    growth,
    growthRate
  };
}

