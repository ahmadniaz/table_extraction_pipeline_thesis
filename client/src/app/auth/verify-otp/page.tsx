'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { motion } from 'framer-motion';
import { Mail, Building2, ArrowLeft, ArrowRight, Clock, CheckCircle, AlertCircle, Moon, Sun } from 'lucide-react';
import toast from 'react-hot-toast';
import Link from 'next/link';

function VerifyOTPContent() {
  const [otp, setOtp] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [isResending, setIsResending] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  const { verifyOTP, requestOTP, isAuthenticated } = useAuth();
  const { theme, setTheme, actualTheme } = useTheme();
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const email = searchParams?.get('email');
  const purpose = searchParams?.get('purpose') as 'login' | 'registration';
  const firstName = searchParams?.get('firstName');
  const lastName = searchParams?.get('lastName');

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, router]);

  // Redirect if no email or purpose
  useEffect(() => {
    if (!email || !purpose) {
      router.push('/landing');
    }
  }, [email, purpose, router]);

  // Countdown timer for resend button
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const handleOtpChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setOtp(value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (otp.length !== 6) {
      toast.error('Please enter a valid 6-digit code');
      return;
    }

    setIsLoading(true);
    try {
      await verifyOTP({ email: email!, otp, purpose: purpose! });
      toast.success(purpose === 'login' ? 'Login successful!' : 'Account created and verified successfully!');
      router.push('/');
    } catch (error: any) {
      toast.error(error.message || 'OTP verification failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (countdown > 0) return;
    
    setIsResending(true);
    try {
      await requestOTP({ email: email!, purpose: purpose! });
      setCountdown(60); // 60 second cooldown
      toast.success('Verification code sent!');
    } catch (error: any) {
      toast.error(error.message || 'Failed to resend OTP');
    } finally {
      setIsResending(false);
    }
  };

  const handleBack = () => {
    router.push('/auth');
  };

  const formatEmail = (email: string) => {
    const [username, domain] = email.split('@');
    return `${username.slice(0, 2)}***@${domain}`;
  };

  if (!email || !purpose) {
    return null; // Will redirect
  }

  return (
    <div className={`min-h-screen flex items-center justify-center p-4 ${actualTheme === 'dark' ? 'dark' : ''}`}>
      <div className="absolute inset-0 bg-slate-50 dark:bg-slate-900"></div>
      <div className="w-full max-w-md relative z-10">
        {/* Theme Toggle */}
        <div className="absolute top-4 right-4 z-20">
          <button
            onClick={() => setTheme(actualTheme === 'dark' ? 'light' : 'dark')}
            className="p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm cursor-pointer"
            aria-label={`Switch to ${actualTheme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {actualTheme === 'dark' ? <Sun className="w-5 h-5 text-slate-300" /> : <Moon className="w-5 h-5 text-slate-600" />}
          </button>
        </div>
        {/* Logo and Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-8"
        >
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-green-500 to-blue-500 rounded-2xl mb-4 shadow-lg">
            <Mail className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-slate-800 via-slate-700 to-slate-600 dark:from-slate-100 dark:via-slate-200 dark:to-slate-300 bg-clip-text text-transparent mb-2">
            Verify Your Email
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            {purpose === 'login' ? 'Complete your login' : 'Complete your registration'}
          </p>
        </motion.div>

        {/* OTP Verification Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-8 border border-slate-200 dark:border-slate-700"
        >
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">
              Enter Verification Code
            </h2>
            <p className="text-slate-600 dark:text-slate-400">
              We&apos;ve sent a 6-digit verification code to
            </p>
            <p className="text-slate-800 dark:text-slate-200 font-semibold mt-1">
              {formatEmail(email)}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* OTP Input */}
            <div>
              <label htmlFor="otp" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                Verification Code
              </label>
              <div className="relative">
                <input
                  id="otp"
                  type="text"
                  value={otp}
                  onChange={handleOtpChange}
                  className="block w-full px-4 py-4 text-center text-2xl font-mono tracking-widest border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-400"
                  placeholder="000000"
                  maxLength={6}
                  required
                  disabled={isLoading}
                />
              </div>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 text-center">
                Enter the 6-digit code sent to your email
              </p>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3">
              <motion.button
                type="submit"
                disabled={isLoading || otp.length !== 6}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-4 rounded-xl font-semibold hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center shadow-lg hover:shadow-xl cursor-pointer"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    Verify Code
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </motion.button>

              <div className="flex space-x-3">
                <motion.button
                  type="button"
                  onClick={handleBack}
                  disabled={isLoading}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="flex-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 py-3 px-4 rounded-xl font-semibold hover:bg-slate-200 dark:hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center cursor-pointer"
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back
                </motion.button>

                <motion.button
                  type="button"
                  onClick={handleResend}
                  disabled={isLoading || isResending || countdown > 0}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="flex-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 py-3 px-4 rounded-xl font-semibold hover:bg-green-200 dark:hover:bg-green-900/50 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center cursor-pointer"
                >
                  {isResending ? (
                    <div className="w-4 h-4 border-2 border-green-600 border-t-transparent rounded-full animate-spin" />
                  ) : countdown > 0 ? (
                    <>
                      <Clock className="mr-2 h-4 w-4" />
                      {countdown}s
                    </>
                  ) : (
                    'Resend Code'
                  )}
                </motion.button>
              </div>
            </div>
          </form>

          {/* Help Text */}
          <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start">
              <CheckCircle className="h-5 w-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" />
              <div className="text-sm text-blue-700 dark:text-blue-300">
                <p className="font-medium">Didn&apos;t receive the code?</p>
                <ul className="mt-2 space-y-1 text-xs">
                  <li>• Check your spam/junk folder</li>
                  <li>• Make sure you entered the correct email address</li>
                  <li>• Wait a few minutes and try resending</li>
                  <li>• Contact support if the problem persists</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Development Note */}
          {process.env.NODE_ENV === 'development' && (
            <div className="mt-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
              <div className="flex items-start">
                <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5 mr-2 flex-shrink-0" />
                <div className="text-xs text-yellow-700 dark:text-yellow-300">
                  <p className="font-medium">Development Mode</p>
                  <p>Check your server console for the OTP code if email is not configured.</p>
                </div>
              </div>
            </div>
          )}
        </motion.div>

      </div>
    </div>
  );
}

// Loading component for Suspense fallback
function VerifyOTPLoading() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo and Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl mb-4 shadow-lg">
            <Building2 className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-slate-800 via-slate-700 to-slate-600 dark:from-slate-100 dark:via-slate-200 dark:to-slate-300 bg-clip-text text-transparent mb-2">
            Commission Tracker
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Secure access to your business dashboard
          </p>
        </div>

        {/* Loading Form */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-8 border border-slate-200 dark:border-slate-700">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-green-500 to-blue-500 rounded-2xl mb-4 shadow-lg">
              <Mail className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">
              Loading Verification
            </h2>
            <p className="text-slate-600 dark:text-slate-400 mb-6">
              Please wait while we prepare your verification...
            </p>
            <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main export with Suspense boundary
export default function VerifyOTPPage() {
  return (
    <Suspense fallback={<VerifyOTPLoading />}>
      <VerifyOTPContent />
    </Suspense>
  );
}
