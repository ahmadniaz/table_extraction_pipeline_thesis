/**
 * Insights Engine
 * Generates intelligent business insights from commission data analysis
 */

import {
  identifyTopPerformingCarriers,
  detectSeasonalPatterns,
  calculatePortfolioDiversification,
  calculateCommissionGrowth,
  formatCurrency,
  formatPercentage
} from './analyticsUtils';

export interface Insight {
  type: 'achievement' | 'opportunity' | 'alert' | 'warning';
  category: 'performance' | 'carrier' | 'seasonal' | 'risk' | 'processing';
  title: string;
  message: string;
  action: string;
  priority: 'high' | 'medium' | 'low';
  metric?: string;
  clickAction?: string;
}

interface AnalysisData {
  commissionData: any[];
  stats: any;
  carriers: any[];
  previousYearData?: any[];
  pendingCount?: number;
  approvedCount?: number;
  rejectedCount?: number;
}

/**
 * Main insights generation function
 */
export function generateInsights(data: AnalysisData): Insight[] {
  const insights: Insight[] = [];
  
  // Performance insights
  insights.push(...generatePerformanceInsights(data));
  
  // Carrier insights
  insights.push(...generateCarrierInsights(data));
  
  // Seasonal insights
  insights.push(...generateSeasonalInsights(data));
  
  // Risk insights
  insights.push(...generateRiskInsights(data));
  
  // Processing insights
  insights.push(...generateProcessingInsights(data));
  
  // Sort by priority and return top insights
  return insights
    .sort((a, b) => {
      const priorityOrder = { high: 0, medium: 1, low: 2 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    })
    .slice(0, 6); // Return top 6 insights
}

/**
 * Generate performance-related insights
 */
function generatePerformanceInsights(data: AnalysisData): Insight[] {
  const insights: Insight[] = [];
  const { stats, commissionData, previousYearData } = data;
  
  // Total commission achievement
  if (stats?.total_commission && stats.total_commission > 0) {
    const formattedAmount = formatCurrency(stats.total_commission);
    
    // Check if it's a milestone
    if (stats.total_commission >= 1000000) {
      insights.push({
        type: 'achievement',
        category: 'performance',
        title: 'Million Dollar Milestone! 🎉',
        message: `Congratulations! You've crossed ${formattedAmount} in total commissions. This is a significant achievement.`,
        action: 'View Details',
        priority: 'high',
        metric: formattedAmount,
        clickAction: 'earned-commission'
      });
    } else if (stats.total_commission >= 500000) {
      insights.push({
        type: 'achievement',
        category: 'performance',
        title: 'Strong Performance',
        message: `You've earned ${formattedAmount} in total commissions. Keep up the excellent work!`,
        action: 'View Breakdown',
        priority: 'medium',
        metric: formattedAmount,
        clickAction: 'earned-commission'
      });
    }
  }
  
  // Year-over-year growth
  if (previousYearData && commissionData) {
    const currentTotal = commissionData.reduce((sum: number, d: any) => sum + (d.commission_earned || 0), 0);
    const previousTotal = previousYearData.reduce((sum: number, d: any) => sum + (d.commission_earned || 0), 0);
    const growth = calculateCommissionGrowth(currentTotal, previousTotal);
    
    if (growth > 20) {
      insights.push({
        type: 'achievement',
        category: 'performance',
        title: 'Exceptional Growth',
        message: `Commission revenue increased by ${formatPercentage(growth)} compared to last year. You're on a strong growth trajectory!`,
        action: 'View Trend',
        priority: 'high',
        metric: `+${formatPercentage(growth)}`,
        clickAction: 'earned-commission'
      });
    } else if (growth < -10) {
      insights.push({
        type: 'alert',
        category: 'performance',
        title: 'Revenue Decline Detected',
        message: `Commission revenue decreased by ${formatPercentage(Math.abs(growth))} compared to last year. Consider reviewing carrier relationships and market conditions.`,
        action: 'Investigate',
        priority: 'high',
        metric: `${formatPercentage(growth)}`,
        clickAction: 'earned-commission'
      });
    }
  }
  
  // Average commission per statement
  if (stats?.total_commission && stats?.total_statements) {
    const avgCommission = stats.total_commission / stats.total_statements;
    
    if (avgCommission > 25000) {
      insights.push({
        type: 'achievement',
        category: 'performance',
        title: 'High-Value Statements',
        message: `Average commission per statement is ${formatCurrency(avgCommission)}. You're focusing on high-value opportunities.`,
        action: 'Analyze',
        priority: 'medium',
        metric: formatCurrency(avgCommission),
        clickAction: 'earned-commission'
      });
    }
  }
  
  return insights;
}

/**
 * Generate carrier-related insights
 */
function generateCarrierInsights(data: AnalysisData): Insight[] {
  const insights: Insight[] = [];
  const { commissionData, carriers } = data;
  
  if (!commissionData || commissionData.length === 0) return insights;
  
  // Identify top performers
  const topCarriers = identifyTopPerformingCarriers(commissionData, 10);
  
  if (topCarriers.length > 0) {
    const topCarrier = topCarriers[0];
    const avgRate = topCarriers.reduce((sum, c) => sum + c.commissionRate, 0) / topCarriers.length;
    
    // Top performer insight
    if (topCarrier.commissionRate > avgRate * 1.3) {
      insights.push({
        type: 'opportunity',
        category: 'carrier',
        title: 'Top Performing Carrier',
        message: `${topCarrier.name} shows exceptional performance with ${formatPercentage(topCarrier.commissionRate)} commission rate, ${formatPercentage((topCarrier.commissionRate / avgRate - 1) * 100)} above average. Consider expanding this relationship.`,
        action: 'View Carrier',
        priority: 'high',
        metric: formatCurrency(topCarrier.totalCommission),
        clickAction: 'carriers'
      });
    }
    
    // Portfolio concentration
    const diversification = calculatePortfolioDiversification(topCarriers);
    
    if (diversification.risk === 'high') {
      insights.push({
        type: 'warning',
        category: 'risk',
        title: 'High Carrier Concentration',
        message: `Your top carrier represents ${formatPercentage(diversification.topCarrierConcentration)} of total revenue. Consider diversifying to reduce dependency risk.`,
        action: 'Review Portfolio',
        priority: 'high',
        metric: formatPercentage(diversification.topCarrierConcentration),
        clickAction: 'carriers'
      });
    } else if (diversification.top3Concentration < 50) {
      insights.push({
        type: 'achievement',
        category: 'risk',
        title: 'Well-Diversified Portfolio',
        message: `Top 3 carriers represent ${formatPercentage(diversification.top3Concentration)} of revenue. You have good portfolio diversification.`,
        action: 'View Details',
        priority: 'low',
        metric: formatPercentage(diversification.top3Concentration),
        clickAction: 'carriers'
      });
    }
    
    // Identify underperforming carriers
    const lowPerformers = topCarriers.filter(c => c.commissionRate < avgRate * 0.7);
    if (lowPerformers.length > 0) {
      insights.push({
        type: 'alert',
        category: 'carrier',
        title: 'Low-Performing Carriers Detected',
        message: `${lowPerformers.length} carrier(s) show commission rates significantly below average. Review these relationships for optimization opportunities.`,
        action: 'Review Carriers',
        priority: 'medium',
        clickAction: 'carriers'
      });
    }
  }
  
  // New carrier opportunity
  if (carriers && carriers.length > 10) {
    insights.push({
      type: 'achievement',
      category: 'carrier',
      title: 'Strong Carrier Network',
      message: `You're working with ${carriers.length} active carriers. This diversity creates stability and growth opportunities.`,
      action: 'View Network',
      priority: 'low',
      metric: `${carriers.length}`,
      clickAction: 'carriers'
    });
  }
  
  return insights;
}

/**
 * Generate seasonal and trend insights
 */
function generateSeasonalInsights(data: AnalysisData): Insight[] {
  const insights: Insight[] = [];
  const { commissionData } = data;
  
  if (!commissionData || commissionData.length === 0) return insights;
  
  // Extract monthly data for pattern detection
  const monthlyData: { month: string; commission: number }[] = [];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  
  // Initialize months
  months.forEach(month => {
    monthlyData.push({ month, commission: 0 });
  });
  
  // Aggregate monthly commissions
  commissionData.forEach((item: any) => {
    if (item.monthly_breakdown) {
      const keys = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
      keys.forEach((key, index) => {
        monthlyData[index].commission += item.monthly_breakdown[key] || 0;
      });
    }
  });
  
  const patterns = detectSeasonalPatterns(monthlyData);
  
  if (patterns.seasonality === 'high') {
    insights.push({
      type: 'opportunity',
      category: 'seasonal',
      title: 'Strong Seasonal Pattern',
      message: `${patterns.peakMonth} consistently shows peak performance. Plan your resource allocation and capacity for this period.`,
      action: 'View Trends',
      priority: 'medium',
      clickAction: 'earned-commission'
    });
  }
  
  // Current month performance
  const currentMonth = new Date().getMonth();
  const currentMonthCommission = monthlyData[currentMonth]?.commission || 0;
  const avgMonthlyCommission = monthlyData.reduce((sum, d) => sum + d.commission, 0) / 12;
  
  if (currentMonthCommission > avgMonthlyCommission * 1.2) {
    insights.push({
      type: 'achievement',
      category: 'seasonal',
      title: 'Strong Month Performance',
      message: `This month is tracking ${formatPercentage(((currentMonthCommission / avgMonthlyCommission) - 1) * 100)} above your monthly average. Excellent work!`,
      action: 'View Details',
      priority: 'medium',
      metric: formatCurrency(currentMonthCommission),
      clickAction: 'earned-commission'
    });
  }
  
  return insights;
}

/**
 * Generate risk-related insights
 */
function generateRiskInsights(data: AnalysisData): Insight[] {
  const insights: Insight[] = [];
  const { commissionData, stats } = data;
  
  if (!commissionData || commissionData.length === 0) return insights;
  
  // Check for data quality issues
  const missingCarrierData = commissionData.filter((d: any) => !d.carrier_name);
  if (missingCarrierData.length > 0) {
    const percentage = (missingCarrierData.length / commissionData.length) * 100;
    if (percentage > 5) {
      insights.push({
        type: 'alert',
        category: 'risk',
        title: 'Data Quality Issue',
        message: `${formatPercentage(percentage)} of records are missing carrier information. This may affect analytics accuracy.`,
        action: 'Review Data',
        priority: 'medium',
        clickAction: 'carriers'
      });
    }
  }
  
  // Check for variance in commission rates
  const carriers = identifyTopPerformingCarriers(commissionData, 10);
  const rates = carriers.map(c => c.commissionRate);
  const avgRate = rates.reduce((sum, r) => sum + r, 0) / rates.length;
  const variance = Math.sqrt(rates.reduce((sum, r) => sum + Math.pow(r - avgRate, 2), 0) / rates.length);
  
  if (variance > avgRate * 0.5) {
    insights.push({
      type: 'warning',
      category: 'risk',
      title: 'High Rate Variance',
      message: `Commission rates vary significantly across carriers (${formatPercentage(variance)} std dev). Review pricing strategies for consistency.`,
      action: 'Analyze Rates',
      priority: 'medium',
      clickAction: 'carriers'
    });
  }
  
  return insights;
}

/**
 * Generate processing-related insights
 */
function generateProcessingInsights(data: AnalysisData): Insight[] {
  const insights: Insight[] = [];
  const { pendingCount, approvedCount, rejectedCount, stats } = data;
  
  // Pending statements alert
  if (pendingCount && pendingCount > 0) {
    // Calculate potential commission (estimate)
    const avgCommission = stats?.total_commission && stats?.total_statements 
      ? stats.total_commission / stats.total_statements 
      : 25000;
    const potentialCommission = pendingCount * avgCommission;
    
    insights.push({
      type: 'alert',
      category: 'processing',
      title: 'Pending Statements Require Action',
      message: `${pendingCount} statement(s) worth approximately ${formatCurrency(potentialCommission)} in potential commission are awaiting review.`,
      action: 'Review Now',
      priority: 'high',
      metric: `${pendingCount}`,
      clickAction: 'dashboard'
    });
  }
  
  // Success rate insight
  const totalProcessed = (approvedCount || 0) + (rejectedCount || 0);
  if (totalProcessed > 0) {
    const successRate = ((approvedCount || 0) / totalProcessed) * 100;
    
    if (successRate > 95) {
      insights.push({
        type: 'achievement',
        category: 'processing',
        title: 'Excellent Processing Quality',
        message: `${formatPercentage(successRate, 1)} success rate shows high-quality statement processing. Your validation process is working well.`,
        action: 'View Stats',
        priority: 'low',
        metric: formatPercentage(successRate, 1)
      });
    } else if (successRate < 85) {
      insights.push({
        type: 'warning',
        category: 'processing',
        title: 'Processing Quality Concern',
        message: `Success rate of ${formatPercentage(successRate, 1)} is below target. Review rejected statements to identify improvement areas.`,
        action: 'Review Issues',
        priority: 'medium',
        metric: formatPercentage(successRate, 1)
      });
    }
  }
  
  // Upload frequency insight
  if (stats?.total_statements) {
    const avgStatementsPerCarrier = stats.total_carriers > 0 
      ? stats.total_statements / stats.total_carriers 
      : 0;
    
    if (avgStatementsPerCarrier < 5) {
      insights.push({
        type: 'opportunity',
        category: 'processing',
        title: 'Upload More Statements',
        message: `Average of ${avgStatementsPerCarrier.toFixed(1)} statements per carrier. Uploading more historical statements will improve trend analysis and forecasting accuracy.`,
        action: 'Upload Now',
        priority: 'low',
        clickAction: 'dashboard'
      });
    }
  }
  
  return insights;
}

/**
 * Generate forecast insights (basic prediction)
 */
export function generateForecastInsights(monthlyData: { month: string; commission: number }[]): {
  nextMonthForecast: number;
  confidence: 'high' | 'medium' | 'low';
  reasoning: string;
} {
  const validData = monthlyData.filter(d => d.commission > 0);
  
  if (validData.length < 3) {
    return {
      nextMonthForecast: 0,
      confidence: 'low',
      reasoning: 'Insufficient data for accurate forecasting'
    };
  }
  
  // Simple moving average forecast
  const recentMonths = validData.slice(-3);
  const forecast = recentMonths.reduce((sum, d) => sum + d.commission, 0) / recentMonths.length;
  
  // Calculate confidence based on variance
  const avgCommission = validData.reduce((sum, d) => sum + d.commission, 0) / validData.length;
  const variance = validData.reduce((sum, d) => sum + Math.pow(d.commission - avgCommission, 2), 0) / validData.length;
  const stdDev = Math.sqrt(variance);
  const coefficientOfVariation = (stdDev / avgCommission) * 100;
  
  let confidence: 'high' | 'medium' | 'low' = 'low';
  if (coefficientOfVariation < 20) confidence = 'high';
  else if (coefficientOfVariation < 40) confidence = 'medium';
  
  const reasoning = confidence === 'high' 
    ? 'Based on consistent historical patterns'
    : confidence === 'medium'
    ? 'Based on moderate historical variability'
    : 'High variability in historical data';
  
  return {
    nextMonthForecast: forecast,
    confidence,
    reasoning
  };
}

