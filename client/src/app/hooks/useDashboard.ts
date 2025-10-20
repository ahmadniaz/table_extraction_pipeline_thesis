import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

interface DashboardStats {
  total_statements: number;
  total_carriers: number;
  total_premium: number | null;
  policies_count: number | null;
  pending_reviews: number;
  approved_statements: number;
  rejected_statements: number;
}

interface Carrier {
  id: string;
  name: string;
  statement_count: number;
}

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
}

export function useDashboardStats(shouldFetch: boolean = true) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(shouldFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/stats`, {
        withCredentials: true
      });
      setStats(response.data);
    } catch (err: any) {
      // Don't set error for 401s as they're handled by auth interceptor
      if (err.response?.status !== 401) {
        setError(err instanceof Error ? err.message : 'An error occurred');
        console.error('Error fetching dashboard stats:', err);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (shouldFetch) {
      fetchStats();
    }
  }, [fetchStats, shouldFetch]);

  return { stats, loading, error, refetch: fetchStats };
}

export function useCarriers() {
  const [carriers, setCarriers] = useState<Carrier[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCarriers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/carriers`, {
        withCredentials: true
      });
      const data = response.data;
      // Sort carriers alphabetically by name
      const sortedCarriers = data.sort((a: Carrier, b: Carrier) => 
        a.name.localeCompare(b.name)
      );
      setCarriers(sortedCarriers);
    } catch (err: any) {
      // Don't set error for 401s as they're handled by auth interceptor
      if (err.response?.status !== 401) {
        setError(err instanceof Error ? err.message : 'An error occurred');
        console.error('Error fetching carriers:', err);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  return { carriers, loading, error, fetchCarriers };
}

export function useStatements() {
  const [statements, setStatements] = useState<Statement[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatements = useCallback(async (status?: 'pending' | 'approved' | 'rejected') => {
    setLoading(true);
    setError(null);
    try {
      const endpoint = status 
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/statements/${status}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/statements`;
      
      const response = await axios.get(endpoint, {
        withCredentials: true
      });
      const data = response.data;
      setStatements(data);
    } catch (err: any) {
      // Don't set error for 401s as they're handled by auth interceptor
      if (err.response?.status !== 401) {
        setError(err instanceof Error ? err.message : 'An error occurred');
        console.error('Error fetching statements:', err);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  return { statements, loading, error, fetchStatements };
} 

// Earned Commission Hooks
export const useEarnedCommissionStats = (year?: number, shouldFetch: boolean = true) => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(shouldFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = year 
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/stats?year=${year}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/stats`;
      const response = await axios.get(url, {
        withCredentials: true
      });
      setStats(response.data);
    } catch (err: any) {
      // Don't set error for 401s as they're handled by auth interceptor
      if (err.response?.status !== 401) {
        console.error('❌ Error fetching earned commission stats:', err);
        setError('Error fetching earned commission stats');
      }
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => {
    if (shouldFetch) {
      fetchStats();
    }
  }, [fetchStats, shouldFetch]);

  return { stats, loading, error, refetch: fetchStats };
};

export const useGlobalEarnedCommissionStats = (year?: number) => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = year 
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/global/stats?year=${year}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/global/stats`;
      const response = await axios.get(url, {
        withCredentials: true
      });
      setStats(response.data);
    } catch (err) {
      console.error('❌ Error fetching global earned commission stats:', err);
      setError('Error fetching global earned commission stats');
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, loading, error, refetch: fetchStats };
};

export const useGlobalCommissionData = (year?: number) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = year 
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/global/data?year=${year}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/global/data`;
      const response = await axios.get(url, {
        withCredentials: true
      });
      setData(response.data);
    } catch (err) {
      console.error('❌ Error fetching global commission data:', err);
      setError('Error fetching global commission data');
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};

export const useUserSpecificCompanies = () => {
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCompanies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/companies/user-specific`, {
        withCredentials: true
      });
      setCompanies(response.data);
    } catch (err) {
      console.error('❌ Error fetching user-specific companies:', err);
      setError('Error fetching user-specific companies');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCompanies();
  }, [fetchCompanies]);

  return { companies, loading, error, refetch: fetchCompanies };
};

export const useCarrierCommissionStats = (carrierId: string | null) => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    if (!carrierId) {
      setStats(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/carrier/${carrierId}/stats`, {
        withCredentials: true
      });
      setStats(response.data);
    } catch (err) {
      setError('Error fetching carrier commission stats');
      console.error('Error fetching carrier commission stats:', err);
    } finally {
      setLoading(false);
    }
  }, [carrierId]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, loading, error, refetch: fetchStats };
};

export const useCarriersWithCommission = () => {
  const [carriers, setCarriers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCarriers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Use the earned-commission/carriers endpoint which includes total_commission
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/carriers`, {
        withCredentials: true
      });
      console.log('🏢 Carriers with commission data fetched:', response.data);
      setCarriers(response.data);
    } catch (err) {
      setError('Error fetching carriers with commission data');
      console.error('Error fetching carriers with commission data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCarriers();
  }, [fetchCarriers]);

  return { carriers, loading, error, refetch: fetchCarriers };
};

export const useCarrierCommissionData = (carrierId: string | null) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!carrierId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/carriers/${carrierId}/earned-commissions`, {
        withCredentials: true
      });
      setData(response.data);
    } catch (err) {
      setError('Error fetching carrier commission data');
      console.error('Error fetching carrier commission data:', err);
    } finally {
      setLoading(false);
    }
  }, [carrierId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};

export const useAvailableYears = () => {
  const [years, setYears] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchYears = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/earned-commissions/years`, {
        withCredentials: true
      });
      setYears(response.data.years || []);
    } catch (err) {
      console.error('❌ Error fetching available years:', err);
      setError('Error fetching available years');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchYears();
  }, [fetchYears]);

  return { years, loading, error, refetch: fetchYears };
};

export const useAllCommissionData = (year?: number) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = year 
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/earned-commissions?year=${year}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/dashboard/earned-commissions`;
      const response = await axios.get(url, {
        withCredentials: true
      });
      setData(response.data);
    } catch (err) {
      console.error('❌ Error fetching all commission data:', err);
      setError('Error fetching all commission data');
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};

export const useCarrierPieChartData = (year?: number) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = year
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/carriers-detailed?year=${year}`
        : `${process.env.NEXT_PUBLIC_API_URL}/api/earned-commission/carriers-detailed`;
      
      const response = await axios.get(url, { withCredentials: true });
      
      // Filter out carriers with zero commission
      const filteredData = response.data.filter((carrier: any) => 
        (carrier.total_commission || carrier.totalCommission || 0) > 0
      );
      
      console.log('📊 Carrier Pie Chart Data:', filteredData);
      setData(filteredData);
    } catch (err) {
      console.error('❌ Error fetching carrier pie chart data:', err);
      setError('Error fetching carrier pie chart data');
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}; 