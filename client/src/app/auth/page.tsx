'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mail, Building2, User, ArrowRight, AlertCircle, Lock, Eye, EyeOff, 
  Moon, Sun, X, Database, CheckCircle, Shield, TrendingUp, Users, 
  Zap, Award, Check
} from 'lucide-react';
import toast from 'react-hot-toast';
import Link from 'next/link';
import { isEmailAuthorized, getAuthorizedEmails } from '@/utils/emailValidation';

export default function UnifiedAuthPage() {
  const [activeTab, setActiveTab] = useState<'login' | 'signup'>('login');
  const [rememberMe, setRememberMe] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [showPasswordStrength, setShowPasswordStrength] = useState(false);
  const { requestOTP, isAuthenticated } = useAuth();
  const { theme, setTheme, actualTheme } = useTheme();
  const router = useRouter();

  // Login form state
  const [loginData, setLoginData] = useState({
    email: '',
    password: ''
  });
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [isLoginLoading, setIsLoginLoading] = useState(false);
  const [isLoginEmailValid, setIsLoginEmailValid] = useState(true);

  // Signup form state
  const [signupData, setSignupData] = useState({
    email: '',
    firstName: '',
    lastName: '',
    companyName: '',
    password: ''
  });
  const [showSignupPassword, setShowSignupPassword] = useState(false);
  const [isSignupLoading, setIsSignupLoading] = useState(false);
  const [isSignupEmailValid, setIsSignupEmailValid] = useState(true);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, router]);

  // Login handlers
  const handleLoginInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setLoginData(prev => ({ ...prev, [name]: value }));
    
    if (name === 'email') {
      const emailValid = value.trim() === '' || isEmailAuthorized(value);
      setIsLoginEmailValid(emailValid);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!isEmailAuthorized(loginData.email)) {
      toast.error('This email address is not authorized for login');
      return;
    }

    if (!loginData.email || !loginData.password) {
      toast.error('Please fill in all required fields');
      return;
    }
    
    setIsLoginLoading(true);

    try {
      await requestOTP({ email: loginData.email, purpose: 'login' });
      toast.success('Verification code sent to your email!');
      // Reset loading state before navigation to prevent stuck loader
      setIsLoginLoading(false);
      router.push(`/auth/verify-otp?email=${encodeURIComponent(loginData.email)}&purpose=login`);
    } catch (error: any) {
      toast.error(error.message || 'Login failed');
      setIsLoginLoading(false);
    }
  };

  // Password strength calculator
  const calculatePasswordStrength = useCallback((password: string) => {
    let strength = 0;
    if (password.length >= 8) strength += 25;
    if (password.length >= 12) strength += 25;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength += 25;
    if (/\d/.test(password)) strength += 12.5;
    if (/[^a-zA-Z0-9]/.test(password)) strength += 12.5;
    setPasswordStrength(Math.min(strength, 100));
  }, []);

  // Signup handlers
  const handleSignupInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSignupData(prev => ({ ...prev, [name]: value }));

    if (name === 'email') {
      const emailValid = value.trim() === '' || isEmailAuthorized(value);
      setIsSignupEmailValid(emailValid);
    }
    
    if (name === 'password') {
      calculatePasswordStrength(value);
      setShowPasswordStrength(value.length > 0);
    }
  };

  const validateSignupForm = () => {
    if (!signupData.email || !signupData.firstName || !signupData.lastName || !signupData.password) {
      toast.error('Please fill in all required fields');
      return false;
    }

    if (!isEmailAuthorized(signupData.email)) {
      toast.error('This email address is not authorized for registration');
      return false;
    }

    if (signupData.password.length < 6) {
      toast.error('Password must be at least 6 characters long');
      return false;
    }

    return true;
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateSignupForm()) {
      return;
    }

    setIsSignupLoading(true);

    try {
      // Register user first
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/otp/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email: signupData.email,
          password: signupData.password,
          first_name: signupData.firstName,
          last_name: signupData.lastName,
          company_name: signupData.companyName || null
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Registration failed');
      }
      
      toast.success('Verification code sent to your email!');
      
      // Reset loading state before navigation to prevent stuck loader
      setIsSignupLoading(false);
      
      // Redirect to OTP verification
      const params = new URLSearchParams({
        email: signupData.email,
        purpose: 'registration',
        firstName: signupData.firstName,
        lastName: signupData.lastName,
      });
      router.push(`/auth/verify-otp?${params.toString()}`);
    } catch (error: any) {
      toast.error(error.message || 'Signup failed');
      setIsSignupLoading(false);
    }
  };

  const getPasswordStrengthColor = () => {
    if (passwordStrength < 25) return 'bg-red-500';
    if (passwordStrength < 50) return 'bg-orange-500';
    if (passwordStrength < 75) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getPasswordStrengthText = () => {
    if (passwordStrength < 25) return 'Weak';
    if (passwordStrength < 50) return 'Fair';
    if (passwordStrength < 75) return 'Good';
    return 'Strong';
  };

  return (
    <div className={`min-h-screen ${actualTheme === 'dark' ? 'dark' : ''}`}>
      {/* Premium Header */}
      <motion.div 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="fixed top-0 left-0 right-0 z-50 bg-white/70 dark:bg-slate-900/70 backdrop-blur-xl border-b border-slate-200/50 dark:border-slate-700/50"
      >
        <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/landing" className="flex items-center space-x-2 sm:space-x-3 group">
              <div className="w-6 h-6 sm:w-8 sm:h-8 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-lg flex items-center justify-center transition-all duration-300 group-hover:scale-105 group-hover:shadow-lg">
                <img 
                  src="/images/icon.svg" 
                  alt="Commission Tracker Icon" 
                  className="w-5 h-5 object-contain sm:w-5 sm:h-5 text-white"
                />
              </div>
              <div className="h-8 sm:h-10 lg:h-12 flex items-center">
                <img 
                  src="/images/logo.svg" 
                  alt="Commission Tracker" 
                  className="h-full object-contain dark:hidden"
                />
                <img 
                  src="/images/logo-dark.svg" 
                  alt="Commission Tracker" 
                  className="h-full object-contain hidden dark:block"
                />
              </div>
            </Link>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setTheme(actualTheme === 'dark' ? 'light' : 'dark')}
                className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-all duration-300 cursor-pointer"
                aria-label="Toggle theme"
              >
                {actualTheme === 'dark' ? (
                  <Sun className="w-5 h-5 text-slate-400" />
                ) : (
                  <Moon className="w-5 h-5 text-slate-600" />
                )}
              </button>
              <Link
                href="/landing"
                className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-all duration-300"
                aria-label="Close"
              >
                <X className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              </Link>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Premium Split Layout */}
      <div className="flex min-h-screen pt-16">
        {/* Left Panel - Brand Experience (40%) */}
        <motion.div 
          initial={{ x: -50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="hidden lg:flex lg:w-[40%] relative bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 dark:from-blue-900 dark:via-indigo-900 dark:to-purple-900 overflow-hidden"
        >
          {/* Animated Background Pattern */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.1)_1px,transparent_1px)] bg-[length:24px_24px]" />
          </div>
          
          {/* Floating Gradient Orbs */}
          <motion.div
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.3, 0.5, 0.3],
            }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
            className="absolute top-20 left-10 w-72 h-72 bg-blue-400/30 rounded-full blur-3xl"
          />
          <motion.div
            animate={{
              scale: [1.2, 1, 1.2],
              opacity: [0.2, 0.4, 0.2],
            }}
            transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
            className="absolute bottom-20 right-10 w-96 h-96 bg-purple-400/20 rounded-full blur-3xl"
          />

          <div className="relative z-10 flex flex-col justify-between p-12 text-white">
            {/* Top Content */}
            <div className="space-y-8">
              {/* Hero Content */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.2, duration: 0.6 }}
              >
                <div className="inline-block px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-xs font-semibold mb-6">
                  ✨ Enterprise Commission Management
                </div>
                <h1 className="text-4xl xl:text-5xl font-bold leading-tight mb-4">
                  Transform Your
                  <br />
                  <span className="bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent">
                    Commission Tracking
                  </span>
                </h1>
                <p className="text-lg text-blue-100 leading-relaxed max-w-md">
                  Join 50+ companies processing over $50M in commissions monthly with our AI-powered platform.
                </p>
              </motion.div>

              {/* Trust Indicators */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.4, duration: 0.6 }}
                className="space-y-4"
              >
                <div className="flex items-center gap-3 p-4 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10">
                  <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-emerald-500 rounded-xl flex items-center justify-center flex-shrink-0">
                    <Shield className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="font-semibold text-sm">Bank-Level Security</div>
                    <div className="text-xs text-blue-100">SOC 2 Type II Certified</div>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-4 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10">
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-cyan-500 rounded-xl flex items-center justify-center flex-shrink-0">
                    <TrendingUp className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="font-semibold text-sm">99.9% Uptime SLA</div>
                    <div className="text-xs text-blue-100">Enterprise Reliability</div>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-4 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10">
                  <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-pink-500 rounded-xl flex items-center justify-center flex-shrink-0">
                    <Users className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="font-semibold text-sm">50+ Companies</div>
                    <div className="text-xs text-blue-100">Trusted Worldwide</div>
                  </div>
                </div>
              </motion.div>
            </div>

            {/* Bottom - Testimonial */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.6 }}
              className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10"
            >
              <div className="flex items-center gap-2 mb-3">
                {[...Array(5)].map((_, i) => (
                  <Award key={i} className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                ))}
              </div>
              <p className="text-sm italic text-blue-50 mb-3">
                &quot;Commission Tracker revolutionized our sales operations. The automation saved us 20 hours per week.&quot;
              </p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center font-bold">
                  SJ
                </div>
                <div>
                  <div className="font-semibold text-sm">Sarah Johnson</div>
                  <div className="text-xs text-blue-100">VP of Sales, TechCorp</div>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>

        {/* Right Panel - Auth Form (60%) */}
        <motion.div 
          initial={{ x: 50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="flex-1 lg:w-[60%] flex items-center justify-center p-6 sm:p-8 lg:p-12 bg-slate-50 dark:bg-slate-900"
        >
          <div className="w-full max-w-lg">
            {/* Premium Card with Glassmorphism */}
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-slate-200/50 dark:border-slate-700/50 overflow-hidden max-h-[90vh] flex flex-col"
            >
              {/* Tab Header with Sliding Indicator */}
              <div className="relative px-6 sm:px-8 pt-8">
                <div className="flex gap-1 bg-slate-100 dark:bg-slate-700/50 p-1 rounded-xl relative">
                  <motion.div
                    className="absolute inset-y-1 bg-white dark:bg-slate-600 rounded-lg shadow-sm"
                    initial={false}
                    animate={{
                      left: activeTab === 'login' ? '4px' : '50%',
                      right: activeTab === 'login' ? '50%' : '4px',
                    }}
                    transition={{ 
                      duration: 0.3,
                      ease: [0.34, 1.56, 0.64, 1]
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setActiveTab('login')}
                    className={`relative z-10 flex-1 px-6 py-3 text-sm font-semibold rounded-lg transition-colors duration-200 ${
                      activeTab === 'login'
                        ? 'text-slate-900 dark:text-slate-100'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                    }`}
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab('signup')}
                    className={`relative z-10 flex-1 px-6 py-3 text-sm font-semibold rounded-lg transition-colors duration-200 ${
                      activeTab === 'signup'
                        ? 'text-slate-900 dark:text-slate-100'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                    }`}
                  >
                    Create Account
                  </button>
                </div>
              </div>

              {/* Form Content with AnimatePresence */}
              <div className="px-6 sm:px-8 pb-8 pt-6 flex flex-col overflow-y-auto flex-grow">
                <AnimatePresence mode="wait" initial={false}>
                  {activeTab === 'login' ? (
                    <motion.div
                      key="login"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ 
                        duration: 0.3,
                        ease: [0.22, 1, 0.36, 1]
                      }}
                      className="flex flex-col"
                    >
                      <div className="flex-grow">
                        <div className="mb-6">
                          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                            Welcome back
                          </h2>
                          <p className="text-sm text-slate-600 dark:text-slate-400">
                            Sign in to access your commission dashboard
                          </p>
                        </div>

                        <form onSubmit={handleLoginSubmit} className="space-y-5">
                        {/* Email Field */}
                        <div>
                          <label htmlFor="login-email" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                            Work Email
                          </label>
                          <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                              <Mail className={`h-5 w-5 transition-colors ${!isLoginEmailValid && loginData.email ? 'text-red-400' : 'text-slate-400 group-focus-within:text-blue-500'}`} />
                            </div>
                            <input
                              id="login-email"
                              name="email"
                              type="email"
                              value={loginData.email}
                              onChange={handleLoginInputChange}
                              className={`block w-full pl-10 pr-3 py-3.5 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition-all duration-300 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 ${
                                !isLoginEmailValid && loginData.email 
                                  ? 'border-red-300 dark:border-red-500 focus:ring-red-500 bg-red-50 dark:bg-red-900/20' 
                                  : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500 focus:border-blue-500'
                              }`}
                              placeholder="you@company.com"
                              required
                              autoComplete="email"
                            />
                            {loginData.email && isLoginEmailValid && (
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"
                              >
                                <CheckCircle className="h-5 w-5 text-green-500" />
                              </motion.div>
                            )}
                            {!isLoginEmailValid && loginData.email && (
                              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                                <AlertCircle className="h-5 w-5 text-red-400" />
                              </div>
                            )}
                          </div>
                          <AnimatePresence>
                            {!isLoginEmailValid && loginData.email && (
                              <motion.p
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="mt-2 text-xs text-red-600 dark:text-red-400 flex items-center gap-1"
                              >
                                <AlertCircle className="w-3 h-3" />
                                This email is not authorized. Contact your administrator.
                              </motion.p>
                            )}
                          </AnimatePresence>
                        </div>

                        {/* Password Field */}
                        <div>
                          <label htmlFor="login-password" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                            Password
                          </label>
                          <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                              <Lock className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                            </div>
                            <input
                              id="login-password"
                              name="password"
                              type={showLoginPassword ? "text" : "password"}
                              value={loginData.password}
                              onChange={handleLoginInputChange}
                              className="block w-full pl-10 pr-12 py-3.5 border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500"
                              placeholder="••••••••"
                              required
                              autoComplete="current-password"
                            />
                            <button
                              type="button"
                              onClick={() => setShowLoginPassword(!showLoginPassword)}
                              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors cursor-pointer"
                              aria-label="Toggle password visibility"
                            >
                              {showLoginPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                            </button>
                          </div>
                        </div>

                        {/* Remember Me & Forgot Password */}
                        <div className="flex items-center justify-between">
                          <label className="flex items-center cursor-pointer group">
                            <input
                              type="checkbox"
                              checked={rememberMe}
                              onChange={(e) => setRememberMe(e.target.checked)}
                              className="w-4 h-4 text-blue-600 bg-white dark:bg-slate-700 border-slate-300 dark:border-slate-600 rounded focus:ring-2 focus:ring-blue-500 cursor-pointer"
                            />
                            <span className="ml-2 text-sm text-slate-600 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-200 transition-colors">
                              Remember me
                            </span>
                          </label>
                        </div>

                        {/* Submit Button */}
                        <motion.button
                          type="submit"
                          disabled={isLoginLoading || !isLoginEmailValid || !loginData.email || !loginData.password}
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.99 }}
                          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white py-3.5 px-4 rounded-xl font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center shadow-lg hover:shadow-xl cursor-pointer"
                        >
                          {isLoginLoading ? (
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                              className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                            />
                          ) : (
                            <>
                              Sign In to Dashboard
                              <ArrowRight className="ml-2 h-4 w-4" />
                            </>
                          )}
                        </motion.button>

                        {/* Security Badge */}
                        <div className="mt-5 pt-5 border-t border-slate-200 dark:border-slate-700">
                          <div className="flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                            <Shield className="w-3.5 h-3.5" />
                            <span>Protected by 256-bit encryption</span>
                          </div>
                        </div>
                        </form>
                      </div>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="signup"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ 
                        duration: 0.3,
                        ease: [0.22, 1, 0.36, 1]
                      }}
                      className="flex flex-col"
                    >
                      <div className="flex-grow">
                        <div className="mb-6">
                          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                            Create your account
                          </h2>
                          <p className="text-sm text-slate-600 dark:text-slate-400">
                            Join 50+ companies using Commission Tracker
                          </p>
                        </div>

                        <form onSubmit={handleSignupSubmit} className="space-y-5">
                        {/* Name Fields */}
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label htmlFor="firstName" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                              First Name *
                            </label>
                            <div className="relative group">
                              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <User className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                              </div>
                              <input
                                id="firstName"
                                name="firstName"
                                type="text"
                                value={signupData.firstName}
                                onChange={handleSignupInputChange}
                                className="block w-full pl-10 pr-3 py-3.5 border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500"
                                placeholder="First name"
                                required
                                autoComplete="given-name"
                              />
                            </div>
                          </div>
                          <div>
                            <label htmlFor="lastName" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                              Last Name *
                            </label>
                            <div className="relative group">
                              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <User className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                              </div>
                              <input
                                id="lastName"
                                name="lastName"
                                type="text"
                                value={signupData.lastName}
                                onChange={handleSignupInputChange}
                                className="block w-full pl-10 pr-3 py-3.5 border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500"
                                placeholder="Last name"
                                required
                                autoComplete="family-name"
                              />
                            </div>
                          </div>
                        </div>

                        {/* Company Name Field */}
                        <div>
                          <label htmlFor="companyName" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                            Company Name
                          </label>
                          <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                              <Building2 className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                            </div>
                            <input
                              id="companyName"
                              name="companyName"
                              type="text"
                              value={signupData.companyName}
                              onChange={handleSignupInputChange}
                              className="block w-full pl-10 pr-3 py-3.5 border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500"
                              placeholder="Your company (optional)"
                              autoComplete="organization"
                            />
                          </div>
                        </div>

                        {/* Email Field */}
                        <div>
                          <label htmlFor="signup-email" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                            Work Email *
                          </label>
                          <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                              <Mail className={`h-5 w-5 transition-colors ${!isSignupEmailValid && signupData.email ? 'text-red-400' : 'text-slate-400 group-focus-within:text-blue-500'}`} />
                            </div>
                            <input
                              id="signup-email"
                              name="email"
                              type="email"
                              value={signupData.email}
                              onChange={handleSignupInputChange}
                              className={`block w-full pl-10 pr-10 py-3.5 border rounded-xl focus:outline-none focus:ring-2 focus:border-transparent transition-all duration-300 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 ${
                                !isSignupEmailValid && signupData.email 
                                  ? 'border-red-300 dark:border-red-500 focus:ring-red-500 bg-red-50 dark:bg-red-900/20' 
                                  : 'border-slate-200 dark:border-slate-600 focus:ring-blue-500 focus:border-blue-500'
                              }`}
                              placeholder="you@company.com"
                              required
                              autoComplete="email"
                            />
                            {signupData.email && isSignupEmailValid && (
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"
                              >
                                <CheckCircle className="h-5 w-5 text-green-500" />
                              </motion.div>
                            )}
                            {!isSignupEmailValid && signupData.email && (
                              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                                <AlertCircle className="h-5 w-5 text-red-400" />
                              </div>
                            )}
                          </div>
                          <AnimatePresence>
                            {!isSignupEmailValid && signupData.email && (
                              <motion.p
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="mt-2 text-xs text-red-600 dark:text-red-400 flex items-center gap-1"
                              >
                                <AlertCircle className="w-3 h-3" />
                                This email is not authorized. Contact your administrator.
                              </motion.p>
                            )}
                          </AnimatePresence>
                        </div>

                        {/* Password Field with Strength Indicator */}
                        <div>
                          <label htmlFor="signup-password" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                            Password *
                          </label>
                          <div className="relative group">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                              <Lock className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                            </div>
                            <input
                              id="signup-password"
                              name="password"
                              type={showSignupPassword ? "text" : "password"}
                              value={signupData.password}
                              onChange={handleSignupInputChange}
                              className="block w-full pl-10 pr-12 py-3.5 border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500"
                              placeholder="Create strong password"
                              required
                              autoComplete="new-password"
                            />
                            <button
                              type="button"
                              onClick={() => setShowSignupPassword(!showSignupPassword)}
                              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors cursor-pointer"
                              aria-label="Toggle password visibility"
                            >
                              {showSignupPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                            </button>
                          </div>
                          
                          {/* Password Strength Indicator */}
                          <AnimatePresence>
                            {showPasswordStrength && (
                              <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="mt-3 space-y-2"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
                                    Password Strength:
                                  </span>
                                  <span className={`text-xs font-semibold ${
                                    passwordStrength < 50 ? 'text-red-600' : passwordStrength < 75 ? 'text-yellow-600' : 'text-green-600'
                                  }`}>
                                    {getPasswordStrengthText()}
                                  </span>
                                </div>
                                <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                  <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${passwordStrength}%` }}
                                    transition={{ duration: 0.3 }}
                                    className={`h-full ${getPasswordStrengthColor()} rounded-full transition-all duration-300`}
                                  />
                                </div>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  <div className={`flex items-center gap-1 ${signupData.password.length >= 8 ? 'text-green-600' : 'text-slate-400'}`}>
                                    <Check className="w-3 h-3" />
                                    <span>8+ characters</span>
                                  </div>
                                  <div className={`flex items-center gap-1 ${/[A-Z]/.test(signupData.password) && /[a-z]/.test(signupData.password) ? 'text-green-600' : 'text-slate-400'}`}>
                                    <Check className="w-3 h-3" />
                                    <span>Mixed case</span>
                                  </div>
                                  <div className={`flex items-center gap-1 ${/\d/.test(signupData.password) ? 'text-green-600' : 'text-slate-400'}`}>
                                    <Check className="w-3 h-3" />
                                    <span>Number</span>
                                  </div>
                                  <div className={`flex items-center gap-1 ${/[^a-zA-Z0-9]/.test(signupData.password) ? 'text-green-600' : 'text-slate-400'}`}>
                                    <Check className="w-3 h-3" />
                                    <span>Special char</span>
                                  </div>
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>

                        {/* Submit Button */}
                        <motion.button
                          type="submit"
                          disabled={isSignupLoading || !isSignupEmailValid || !signupData.email || !signupData.firstName || !signupData.lastName || !signupData.password || passwordStrength < 50}
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.99 }}
                          className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white py-3.5 px-4 rounded-xl font-semibold focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center shadow-lg hover:shadow-xl cursor-pointer"
                        >
                          {isSignupLoading ? (
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                              className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                            />
                          ) : (
                            <>
                              Create Your Account
                              <ArrowRight className="ml-2 h-4 w-4" />
                            </>
                          )}
                        </motion.button>

                          {/* Terms & Security Badge */}
                          <div className="space-y-3">
                            <p className="text-xs text-center text-slate-500 dark:text-slate-400">
                              By creating an account, you agree to our{' '}
                              <a href="#" className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium">
                                Terms of Service
                              </a>{' '}
                              and{' '}
                              <a href="#" className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium">
                                Privacy Policy
                              </a>
                            </p>
                            <div className="pt-3 border-t border-slate-200 dark:border-slate-700">
                              <div className="flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                                <Shield className="w-3.5 h-3.5" />
                                <span>GDPR Compliant • SOC 2 Type II Certified</span>
                              </div>
                            </div>
                          </div>
                        </form>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Switch Tab Prompt */}
                <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700 text-center">
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {activeTab === 'login' ? (
                      <>
                        New to Commission Tracker?{' '}
                        <button
                          type="button"
                          onClick={() => setActiveTab('signup')}
                          className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-semibold transition-colors"
                        >
                          Create an account
                        </button>
                      </>
                    ) : (
                      <>
                        Already have an account?{' '}
                        <button
                          type="button"
                          onClick={() => setActiveTab('login')}
                          className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-semibold transition-colors"
                        >
                          Sign in
                        </button>
                      </>
                    )}
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Mobile-Only Trust Indicators */}
            <div className="lg:hidden mt-8 space-y-4">
              <div className="flex items-center gap-3 p-4 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-slate-700">
                <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-emerald-500 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Shield className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-sm text-slate-900 dark:text-slate-100">Bank-Level Security</div>
                  <div className="text-xs text-slate-600 dark:text-slate-400">SOC 2 Type II Certified</div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-4 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-slate-700">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-cyan-500 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Users className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="font-semibold text-sm text-slate-900 dark:text-slate-100">Trusted by 50+</div>
                  <div className="text-xs text-slate-600 dark:text-slate-400">Companies Worldwide</div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

