import { useState, useCallback } from 'react';
import { CompanyNameNormalizer } from '../utils/CompanyNameNormalizer';

interface CompanyNormalizationResult {
  original: string;
  normalized: string;
  status: 'existing' | 'normalized' | 'error';
}

interface CarrierInfo {
  carrier_name: string;
  total_commission: number;
  total_invoice: number;
  statement_count: number;
  first_seen: string;
  last_seen: string;
}

export const useCompanyNormalization = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalizeCompanies = useCallback(async (companies: string[]): Promise<CompanyNormalizationResult[]> => {
    setLoading(true);
    setError(null);
    
    try {
      // For now, implement client-side normalization
      // Later, this can be replaced with API call
      const results = companies.map(company => ({
        original: company,
        normalized: CompanyNameNormalizer.normalize(company),
        status: 'normalized' as const
      }));
      
      return results;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getCompanyCarriers = useCallback(async (companyName: string): Promise<{
    companyName: string;
    carriers: CarrierInfo[];
    totalCarriers: number;
    totalCommission: number;
    totalStatements: number;
  }> => {
    // This would typically be an API call
    // For now, return mock data structure
    return {
      companyName,
      carriers: [],
      totalCarriers: 0,
      totalCommission: 0,
      totalStatements: 0
    };
  }, []);

  return {
    normalizeCompanies,
    getCompanyCarriers,
    loading,
    error
  };
};

