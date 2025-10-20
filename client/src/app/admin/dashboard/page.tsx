'use client'
import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import axios from 'axios';
import { 
  Users, 
  Building2, 
  FileText, 
  TrendingUp, 
  DollarSign, 
  Activity,
  ArrowLeft,
  Settings,
  BarChart3,
  Calendar,
  Shield,
  Globe,
  Plus,
  Trash2,
  Edit,
  MoreVertical,
  RotateCcw,
  UserX
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';

interface CompanyStats {
  total_statements: number;
  total_carriers: number;
  total_commission: number;
  pending_reviews: number;
  approved_statements: number;
  rejected_statements: number;
}

interface UserStats {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  total_uploads: number;
  total_approved: number;
  total_rejected: number;
  total_pending: number;
  carriers_worked_with: number;
  total_commission_contributed: number;
}

interface AdminDashboardData {
  company_stats: CompanyStats;
  users: UserStats[];
  total_users: number;
  active_users: number;
}

interface AllowedDomain {
  id: string;
  domain: string;
  company_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export default function AdminDashboard() {
  const { user, logout, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'domains'>('overview');
  const [domains, setDomains] = useState<AllowedDomain[]>([]);
  const [domainLoading, setDomainLoading] = useState(false);
  const [showAddDomain, setShowAddDomain] = useState(false);
  const [newDomain, setNewDomain] = useState('');
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  useEffect(() => {
    // Wait for authentication to complete before fetching data
    if (!authLoading && user) {
      fetchAdminData();
    }
  }, [authLoading, user]);

  useEffect(() => {
    if (activeTab === 'domains') {
      fetchDomains();
    }
  }, [activeTab]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (openDropdown && !target.closest('.dropdown-container')) {
        setOpenDropdown(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [openDropdown]);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/dashboard`, {
        withCredentials: true  // CRITICAL FIX: Ensure cookies are sent
      });
      setData(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      toast.error('Failed to load admin dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchDomains = async () => {
    try {
      setDomainLoading(true);
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/domains`, {
        withCredentials: true  // CRITICAL FIX: Ensure cookies are sent
      });
      setDomains(response.data);
    } catch (err) {
      toast.error('Failed to load domains');
    } finally {
      setDomainLoading(false);
    }
  };

  const addDomain = async () => {
    if (!newDomain.trim()) {
      toast.error('Please enter a domain');
      return;
    }

    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/domains`, {
        domain: newDomain.trim(),
        is_active: true
      }, {
        withCredentials: true  // CRITICAL FIX: Ensure cookies are sent
      });
      toast.success('Domain added successfully');
      setNewDomain('');
      setShowAddDomain(false);
      fetchDomains();
    } catch (err) {
      toast.error('Failed to add domain');
    }
  };

  const deleteDomain = async (domainId: string) => {
    if (!confirm('Are you sure you want to delete this domain?')) {
      return;
    }

    try {
      await axios.delete(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/domains/${domainId}`, {
        withCredentials: true  // CRITICAL FIX: Ensure cookies are sent
      });
      toast.success('Domain deleted successfully');
      fetchDomains();
    } catch (err) {
      toast.error('Failed to delete domain');
    }
  };

  const toggleDomainStatus = async (domainId: string, isActive: boolean) => {
    try {
      await axios.put(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/domains/${domainId}`, {
        is_active: !isActive
      }, {
        withCredentials: true  // CRITICAL FIX: Ensure cookies are sent
      });
      toast.success('Domain status updated');
      fetchDomains();
    } catch (err) {
      toast.error('Failed to update domain status');
    }
  };

  const deleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user? This will permanently remove the user and all their data from the system.')) {
      return;
    }

    try {
      await axios.delete(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/users/${userId}`, {
        withCredentials: true  // CRITICAL FIX: Ensure cookies are sent
      });
      toast.success('User deleted successfully');
      fetchAdminData();
    } catch (err) {
      toast.error('Failed to delete user');
    }
  };

  const resetUserData = async (userId: string) => {
    if (!confirm('Are you sure you want to reset this user\'s data? This will clear all uploaded data but keep the user account active.')) {
      return;
    }

    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/users/${userId}/reset-data`, {}, {
        withCredentials: true  // CRITICAL FIX: Ensure cookies are sent
      });
      toast.success('User data reset successfully');
      fetchAdminData();
    } catch (err) {
      toast.error('Failed to reset user data');
    }
  };

  const updateUserRole = async (userId: string, newRole: string) => {
    try {
      await axios.put(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/users/${userId}/role`, {
        role: newRole
      }, {
        withCredentials: true  // CRITICAL FIX: Ensure cookies are sent
      });
      toast.success('User role updated successfully');
      fetchAdminData();
    } catch (err) {
      toast.error('Failed to update user role');
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-emerald-100 text-emerald-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading || authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-100/50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
            <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          </div>
          <p className="mt-6 text-slate-600 font-medium">Loading Admin Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-100/50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-red-500 to-red-600 rounded-2xl flex items-center justify-center shadow-lg">
            <Activity className="text-white" size={32} />
          </div>
          <p className="mt-6 text-slate-600 font-medium">Error loading dashboard</p>
          <button
            onClick={fetchAdminData}
            className="mt-4 px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const statCards = [
    {
      label: "Total Statements",
      value: data.company_stats.total_statements,
      icon: FileText,
      color: "blue",
      gradient: "from-blue-500 to-indigo-600",
      description: "All uploaded statements"
    },
    {
      label: "Total Carriers",
      value: data.company_stats.total_carriers,
      icon: Building2,
      color: "purple",
      gradient: "from-purple-500 to-violet-600",
      description: "Active carriers"
    },
    {
      label: "Total Commission",
      value: formatCurrency(data.company_stats.total_commission),
      icon: DollarSign,
      color: "green",
      gradient: "from-emerald-500 to-teal-600",
      description: "Commission earned"
    },
    {
      label: "Total Users",
      value: data.total_users,
      icon: Users,
      color: "indigo",
      gradient: "from-indigo-500 to-blue-600",
      description: "Registered users"
    },
    {
      label: "Active Users",
      value: data.active_users,
      icon: Activity,
      color: "emerald",
      gradient: "from-emerald-500 to-green-600",
      description: "Recently active"
    },
    {
      label: "Pending Reviews",
      value: data.company_stats.pending_reviews,
      icon: BarChart3,
      color: "amber",
      gradient: "from-amber-500 to-orange-600",
      description: "Awaiting review"
    }
  ];

  return (
    <ProtectedRoute requireAuth={true} requireAdmin={true}>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-100/50">
      {/* Header */}
      <header className="bg-white/95 backdrop-blur-xl border-b border-slate-200 shadow-xl sticky top-0 z-50">
        <div className="w-[90%] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/')}
                className="p-2 rounded-xl hover:bg-slate-100 transition-colors duration-200"
              >
                <ArrowLeft className="w-6 h-6 text-slate-600" />
              </button>
              <div className="relative">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-600 via-indigo-600 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                  <Shield className="text-white" size={24} />
                </div>
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-to-r from-emerald-400 to-teal-400 rounded-full border-2 border-white shadow-sm"></div>
              </div>
              <div>
                <h1 className="font-bold text-2xl bg-gradient-to-r from-slate-800 via-slate-700 to-slate-600 bg-clip-text text-transparent">
                  Admin Dashboard
                </h1>
                <p className="text-sm text-slate-500 font-medium">Company Overview & User Management</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={logout}
                className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl transition-colors duration-200 font-medium"
              >
                <Settings className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="w-[90%] mx-auto px-6 py-4">
        <div className="bg-white/95 backdrop-blur-xl rounded-2xl border border-slate-200 shadow-lg p-2">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('overview')}
              className={`flex-1 px-6 py-3 rounded-xl font-semibold transition-all duration-200 ${
                activeTab === 'overview'
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Overview
              </div>
            </button>
            <button
              onClick={() => setActiveTab('domains')}
              className={`flex-1 px-6 py-3 rounded-xl font-semibold transition-all duration-200 ${
                activeTab === 'domains'
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                <Globe className="w-4 h-4" />
                Domain Management
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="w-[90%] mx-auto px-6 py-8">
        {activeTab === 'overview' && (
          <>
            {/* Company Overview Stats */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-800 mb-6">Company Overview</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
            {statCards.map((card, i) => {
              const Icon = card.icon;
              return (
                <div key={i} className="bg-white/95 backdrop-blur-xl rounded-2xl border border-slate-200 shadow-lg p-6 hover:shadow-xl transition-all duration-300 hover:scale-105">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 bg-gradient-to-br ${card.gradient} rounded-xl flex items-center justify-center shadow-lg`}>
                      <Icon className="text-white" size={24} />
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-slate-600 font-semibold mb-1">{card.label}</p>
                    <p className="text-2xl font-bold text-slate-800 mb-1">{card.value}</p>
                    <p className="text-xs text-slate-500">{card.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-white/95 backdrop-blur-xl rounded-2xl border border-slate-200 shadow-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-slate-800">Company Users</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full company-table">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left py-4 px-4 font-bold text-slate-800">User</th>
                  <th className="text-left py-4 px-4 font-bold text-slate-800">Role</th>
                  <th className="text-left py-4 px-4 font-bold text-slate-800">Status</th>
                  <th className="text-left py-4 px-4 font-bold text-slate-800">Uploads</th>
                  <th className="text-left py-4 px-4 font-bold text-slate-800">Carriers</th>
                  <th className="text-left py-4 px-4 font-bold text-slate-800">Commission</th>
                  <th className="text-left py-4 px-4 font-bold text-slate-800">Last Login</th>
                  <th className="text-left py-4 px-4 font-bold text-slate-800">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((user) => (
                  <tr key={user.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                          {user.first_name?.[0] || user.email[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-slate-800">
                            {user.first_name && user.last_name 
                              ? `${user.first_name} ${user.last_name}`
                              : user.email
                            }
                          </p>
                          <p className="text-sm text-slate-500">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                        <select
                        value={user.role}
                        onChange={(e) => updateUserRole(user.id, e.target.value)}
                        className={`px-3 py-1 rounded-full text-sm font-semibold capitalize border-0 focus:ring-2 focus:ring-blue-500 transition-all duration-200 ${
                          user.role === 'admin' 
                            ? 'bg-purple-100 text-purple-800 border border-purple-200' 
                            : user.role === 'user'
                            ? 'bg-blue-100 text-blue-800 border border-blue-200'
                            : 'bg-slate-100 text-slate-800 border border-slate-200'
                        }`}
                      >
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                        <option value="read_only">Read Only</option>
                      </select>
                    </td>
                    <td className="py-4 px-4">
                      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                        user.is_active 
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' 
                          : 'bg-red-100 text-red-800 border border-red-200'
                      }`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <div className="text-center">
                        <p className="font-semibold text-slate-800">{user.total_uploads}</p>
                        <div className="flex justify-center gap-1 text-xs text-slate-500">
                          <span className="text-emerald-600">{user.total_approved}✓</span>
                          <span className="text-red-600">{user.total_rejected}✗</span>
                          <span className="text-yellow-600">{user.total_pending}⏳</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <p className="font-semibold text-slate-800">{user.carriers_worked_with}</p>
                    </td>
                    <td className="py-4 px-4">
                      <p className="font-semibold text-slate-800">{formatCurrency(user.total_commission_contributed)}</p>
                    </td>
                    <td className="py-4 px-4">
                      <p className="text-sm text-slate-600">
                        {user.last_login ? formatDate(user.last_login) : 'Never'}
                      </p>
                    </td>
                    <td className="py-4 px-4">
                      <div className="relative dropdown-container">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setOpenDropdown(openDropdown === user.id ? null : user.id);
                          }}
                          className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                          title="More Options"
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>
                        
                        {openDropdown === user.id && (
                          <div className="absolute right-0 top-10 bg-white border border-slate-200 rounded-xl shadow-xl z-10 min-w-[200px]">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                resetUserData(user.id);
                                setOpenDropdown(null);
                              }}
                              className="w-full px-4 py-3 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2 transition-colors rounded-t-xl"
                            >
                              <RotateCcw className="w-4 h-4" />
                              Reset User Data
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteUser(user.id);
                                setOpenDropdown(null);
                              }}
                              className="w-full px-4 py-3 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors rounded-b-xl"
                            >
                              <UserX className="w-4 h-4" />
                              Delete User
                            </button>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.users.length === 0 && (
            <div className="text-center py-12">
              <Users className="mx-auto text-slate-400" size={48} />
              <p className="text-slate-600 mt-4">No users found</p>
            </div>
          )}
        </div>
          </>
        )}

        {activeTab === 'domains' && (
          <div className="bg-white/95 backdrop-blur-xl rounded-2xl border border-slate-200 shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-slate-800">Domain Management</h2>
              <button
                onClick={() => setShowAddDomain(true)}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
              >
                <Plus className="w-4 h-4" />
                Add Domain
              </button>
            </div>

            {/* Add Domain Form */}
            {showAddDomain && (
              <div className="mb-6 p-6 bg-slate-50 rounded-xl border border-slate-200">
                <h3 className="text-lg font-semibold text-slate-800 mb-4">Add New Domain</h3>
                <div className="flex gap-4">
                  <input
                    type="text"
                    placeholder="Enter domain (e.g., company.com)"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    className="flex-1 px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
                  />
                  <button
                    onClick={addDomain}
                    className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
                  >
                    Add
                  </button>
                  <button
                    onClick={() => {
                      setShowAddDomain(false);
                      setNewDomain('');
                    }}
                    className="px-6 py-3 bg-slate-500 text-white rounded-xl font-semibold hover:bg-slate-600 transition-all duration-200"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Domains List */}
            {domainLoading ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg animate-pulse mx-auto">
                  <Globe className="text-white" size={32} />
                </div>
                <p className="mt-6 text-slate-600 font-medium">Loading domains...</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full company-table">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="text-left py-4 px-4 font-bold text-slate-800">Domain</th>
                      <th className="text-left py-4 px-4 font-bold text-slate-800">Status</th>
                      <th className="text-left py-4 px-4 font-bold text-slate-800">Created</th>
                      <th className="text-left py-4 px-4 font-bold text-slate-800">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {domains.map((domain) => (
                      <tr key={domain.id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                              <Globe className="w-4 h-4" />
                            </div>
                            <div>
                              <p className="font-medium text-slate-800">{domain.domain}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <button
                            onClick={() => toggleDomainStatus(domain.id, domain.is_active)}
                            className={`px-3 py-1 rounded-full text-sm font-semibold transition-colors ${
                              domain.is_active
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-200 hover:bg-emerald-200'
                                : 'bg-red-100 text-red-800 border border-red-200 hover:bg-red-200'
                            }`}
                          >
                            {domain.is_active ? 'Active' : 'Inactive'}
                          </button>
                        </td>
                        <td className="py-4 px-4">
                          <p className="text-sm text-slate-600">
                            {formatDate(domain.created_at)}
                          </p>
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => deleteDomain(domain.id)}
                              className="p-2 text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                              title="Delete Domain"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {domains.length === 0 && (
                  <div className="text-center py-12">
                    <Globe className="mx-auto text-slate-400" size={48} />
                    <p className="text-slate-600 mt-4">No domains configured</p>
                    <p className="text-sm text-slate-500 mt-2">Add a domain to allow users with that email domain to register</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
      </div>
    </ProtectedRoute>
  );
}