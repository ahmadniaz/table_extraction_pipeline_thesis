'use client'
import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import DashboardTab from "./components/dashboardTab/DashboardTab";
import CarrierTab from "./components/carrierTab/CarrierTab";
import EarnedCommissionTab from "./components/dashboardTab/EarnedCommissionTab";
import PremiumAnalyticsTab from "./components/dashboardTab/PremiumAnalyticsTab";

import { 
  Database, 
  BarChart3, 
  DollarSign, 
  Settings, 
  LogOut, 
  ChevronDown, 
  User, 
  Menu,
  X,
  Bell,
  Search,
  Moon,
  Sun,
  ChevronLeft,
  ChevronRight,
  Upload
} from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

function HomePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, logout } = useAuth();
  const { theme, setTheme, actualTheme } = useTheme();
  const [tab, setTab] = useState<"dashboard" | "carriers" | "earned-commission" | "analytics">("analytics");
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Handle URL parameters for tab selection
  useEffect(() => {
    const tabParam = searchParams?.get('tab')
    if (tabParam && ['dashboard', 'carriers', 'earned-commission', 'analytics'].includes(tabParam)) {
      setTab(tabParam as "dashboard" | "carriers" | "earned-commission" | "analytics")
    } else {
      // Default to analytics if no tab parameter or invalid tab
      setTab("analytics")
    }
  }, [searchParams])

  // Handle responsive behavior
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setSidebarOpen(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showUserDropdown) {
        setShowUserDropdown(false);
      }
    };

    if (showUserDropdown) {
      document.addEventListener('click', handleClickOutside);
    }

    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [showUserDropdown])

  const tabConfig = [
    {
      id: "analytics" as const,
      label: "Analytics",
      icon: BarChart3,
      description: "Commission Analytics & Insights",
      gradient: "from-emerald-600 via-teal-600 to-cyan-600",
      bgGradient: "from-emerald-50 via-teal-50 to-cyan-50"
    },
    {
      id: "dashboard" as const,
      label: "Upload",
      icon: Upload,
      description: "Upload & Process Documents",
      gradient: "from-blue-600 via-indigo-600 to-purple-600",
      bgGradient: "from-blue-50 via-indigo-50 to-purple-50"
    },
    {
      id: "earned-commission" as const,
      label: "Earned Commission",
      icon: DollarSign,
      description: "Commission Tracking & Analysis",
      gradient: "from-violet-600 via-purple-600 to-fuchsia-600",
      bgGradient: "from-violet-50 via-purple-50 to-fuchsia-50"
    },
    {
      id: "carriers" as const,
      label: "Carriers",
      icon: Database,
      description: "Manage Carriers & Statements",
      gradient: "from-orange-600 via-red-600 to-pink-600",
      bgGradient: "from-orange-50 via-red-50 to-pink-50"
    }
  ];

  return (
    <div className={`min-h-screen flex ${actualTheme === 'dark' ? 'dark' : ''}`}>
      {/* Mobile Overlay */}
      {isMobile && sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      <div 
        className={`
          ${isMobile 
            ? `fixed top-0 left-0 h-full z-50 transform transition-transform duration-300 ${
                sidebarOpen ? 'translate-x-0' : '-translate-x-full'
              } w-80`
            : `fixed top-0 left-0 h-full ${sidebarCollapsed ? 'w-20 hover:w-80' : 'w-80'} transition-all duration-300 z-30`
          } 
          bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col shadow-xl group scrollbar-none overflow-hidden
        `}
        onMouseEnter={() => !isMobile && setSidebarCollapsed(false)}
        onMouseLeave={() => !isMobile && setSidebarCollapsed(true)}
      >
        {/* Sidebar Header */}
        <div className="px-7 py-6 border-b border-slate-200 dark:border-slate-700 flex-shrink-0">
          <div className="flex items-center justify-center">
            <div className="relative">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                <img 
                  src="/images/icon.svg" 
                  alt="Commission Tracker Icon" 
                  className="w-7 h-7 object-contain"
                />
              </div>
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-gradient-to-r from-emerald-400 to-teal-400 rounded-full border-2 border-white shadow-sm"></div>
            </div>
            <div className={`ml-3 transition-all duration-300 ${
              sidebarCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100'
            }`}>
              <h1 className="font-bold text-lg bg-gradient-to-r from-slate-800 via-slate-700 to-slate-600 dark:from-slate-100 dark:via-slate-200 dark:to-slate-300 bg-clip-text text-transparent whitespace-nowrap">
                Commission Tracker
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap">Pinecrest Professional SaaS</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-2 px-3 py-4 transition-all duration-300 scrollbar-none overflow-y-auto">
          {tabConfig.map((tabItem) => {
            const Icon = tabItem.icon;
            const isActive = tab === tabItem.id;
            
            return (
              <button
                key={tabItem.id}
                onClick={() => {
                  if (tabItem.id === 'analytics') {
                    router.push('/');
                  } else {
                    router.push(`/?tab=${tabItem.id}`);
                  }
                  // Close sidebar on mobile after navigation
                  if (isMobile) {
                    setSidebarOpen(false);
                  }
                }}
                className={`w-full flex items-center justify-between px-2 py-3 rounded-lg transition-all cursor-pointer border border-transparent min-h-[48px] ${
                  isActive && !sidebarCollapsed
                    ? 'bg-blue-100 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300' 
                    : 'hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'
                }`}
                aria-label={`Navigate to ${tabItem.label}`}
                title={sidebarCollapsed ? `${tabItem.label} - ${tabItem.description}` : tabItem.description}
                aria-current={isActive ? "page" : undefined}
              >
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 dark:from-blue-600 dark:to-indigo-700 rounded-lg flex items-center justify-center shadow-sm">
                      <Icon size={16} className="text-white" />
                    </div>
                    {/* Blue dot indicator for collapsed sidebar when active */}
                    {isActive && sidebarCollapsed && (
                      <div className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full shadow-sm animate-pulse"></div>
                    )}
                  </div>
                  <div className={`text-left flex-1 min-w-0 transition-all duration-300 ${
                    sidebarCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100 w-auto'
                  }`}>
                    <div className="font-medium text-slate-700 dark:text-slate-300 truncate">{tabItem.label}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 truncate">{tabItem.description}</div>
                  </div>
                </div>
                <div className={`w-4 h-4 flex items-center justify-center transition-all duration-300 flex-shrink-0 ${
                  sidebarCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100'
                }`}>
                  {isActive && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full shadow-sm animate-pulse"></div>
                  )}
                </div>
              </button>
            );
          })}
        </nav>

        {/* User Profile Section */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex-shrink-0">
          <div className="relative group">
            <button
              onClick={() => setShowUserDropdown(!showUserDropdown)}
              className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold text-sm shadow-lg flex-shrink-0">
                {user?.first_name?.[0] || user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <div className={`flex-1 text-left transition-opacity duration-300 ${
                sidebarCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100'
              }`}>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">
                  {user?.first_name && user?.last_name 
                    ? `${user.first_name} ${user.last_name}`
                    : user?.email
                  }
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 capitalize">{user?.role}</p>
              </div>
              <ChevronDown className={`w-4 h-4 text-slate-500 transition-all duration-300 ${
                sidebarCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100'
              } ${showUserDropdown ? 'rotate-180' : ''}`} />
            </button>
            
            {/* Tooltip for collapsed state */}
            {sidebarCollapsed && (
              <div className="absolute left-full ml-2 px-3 py-2 bg-slate-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50">
                {user?.first_name && user?.last_name 
                  ? `${user.first_name} ${user.last_name}`
                  : user?.email
                }
                <div className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1 w-2 h-2 bg-slate-800 rotate-45"></div>
              </div>
            )}

            {/* Dropdown Menu */}
            {showUserDropdown && !sidebarCollapsed && (
              <div 
                className="absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700 z-50 animate-in fade-in-0 zoom-in-95 duration-200"
                role="menu"
                aria-label="User menu options"
              >
                <div className="p-3 border-b border-slate-200 dark:border-slate-700">
                  <div className="font-medium text-slate-700 dark:text-slate-300 text-sm">
                    {user?.first_name && user?.last_name 
                      ? `${user.first_name} ${user.last_name}`
                      : user?.email
                    }
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 capitalize">{user?.role}</div>
                </div>
                <div className="p-2">
                  {user?.role === 'admin' && (
                    <button
                      onClick={() => {
                        router.push('/admin/dashboard');
                        setShowUserDropdown(false);
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 mb-2 cursor-pointer"
                      aria-label="Open admin dashboard"
                      role="menuitem"
                    >
                      <Settings className="w-4 h-4" />
                      <span>Admin Dashboard</span>
                    </button>
                  )}
                  <button
                    onClick={() => {
                      logout();
                      setShowUserDropdown(false);
                    }}
                    className="w-full flex items-center gap-3 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 cursor-pointer"
                    aria-label="Logout from application"
                    role="menuitem"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col min-w-0 ${sidebarCollapsed ? 'ml-20' : 'ml-80'} transition-all duration-300`}>
        {/* Top Header */}
        <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
                {tabConfig.find(t => t.id === tab)?.label}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {tabConfig.find(t => t.id === tab)?.description}
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              <button className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
                <Search className="w-5 h-5 text-slate-500 dark:text-slate-400" />
              </button>
              <button className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors relative">
                <Bell className="w-5 h-5 text-slate-500 dark:text-slate-400" />
                <div className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></div>
              </button>
              <button
                onClick={() => setTheme(actualTheme === 'dark' ? 'light' : 'dark')}
                className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                aria-label={`Switch to ${actualTheme === 'dark' ? 'light' : 'dark'} mode`}
              >
                {actualTheme === 'dark' ? <Sun className="w-5 h-5 text-slate-500 dark:text-slate-400" /> : <Moon className="w-5 h-5 text-slate-500 dark:text-slate-400" />}
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-6 bg-slate-50 dark:bg-slate-900 overflow-y-auto main-content-scroll">
          <div className="max-w-none">
            {tab === "analytics" && <PremiumAnalyticsTab onNavigate={(newTab) => router.push(`/?tab=${newTab}`)} />}
            {tab === "dashboard" && <DashboardTab />}
            {tab === "earned-commission" && <EarnedCommissionTab />}
            {tab === "carriers" && <CarrierTab />}
          </div>
        </main>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <ProtectedRoute requireAuth={true}>
      <Suspense fallback={
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-100/50 flex items-center justify-center">
          <div className="text-center">
            <div className="relative">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg animate-pulse">
                <img 
                  src="/images/icon.svg" 
                  alt="Commission Tracker Icon" 
                  className="w-14 h-14 object-contain"
                />
              </div>
              <div className="absolute -top-2 -right-2 w-6 h-6 bg-gradient-to-r from-emerald-400 to-teal-400 rounded-full animate-ping"></div>
            </div>
            <p className="mt-6 text-slate-600 font-medium">Loading Commission Tracker...</p>
          </div>
        </div>
      }>
        <HomePageContent />
      </Suspense>
    </ProtectedRoute>
  );
}
