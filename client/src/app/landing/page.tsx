'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/context/ThemeContext';
import { useThemeHydration } from '@/hooks/useThemeHydration';
import LoadingScreen from '@/app/components/LoadingScreen';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Database, 
  Moon,
  Sun,
  Menu,
  X
} from 'lucide-react';
import Link from 'next/link';

// Import new components
import {
  Hero,
  CompanyCarousel,
  FeatureGrid,
  BenefitsSection,
  StepScrollStorytelling,
  UseCaseShowcase,
  RegistrationForm,
  HeroScrollStorytelling
} from './components';

export default function LandingPage() {
  const router = useRouter();
  const { theme, setTheme, actualTheme } = useTheme();
  
  // Custom setTheme for landing with specific storage key
  const setLandingTheme = (newTheme: 'light' | 'dark' | 'system') => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('commission-tracker-theme-landing', newTheme);
    }
    setTheme(newTheme);
  };
  const { mounted, isDark } = useThemeHydration();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isHeaderVisible, setIsHeaderVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  const handleGetStarted = (email: string) => {
    // Navigate to unified auth page
    router.push('/auth');
  };

  // Force light mode for landing page only if no preference is saved
  useEffect(() => {
    if (mounted) {
      const savedTheme = localStorage.getItem('commission-tracker-theme-landing');
      if (!savedTheme && theme !== 'light') {
        setLandingTheme('light');
      }
    }
  }, [mounted, theme]);

  // Handle scroll behavior for header visibility
  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      
      // Show header when scrolling up or at the top
      if (currentScrollY < lastScrollY || currentScrollY < 10) {
        setIsHeaderVisible(true);
      } 
      // Hide header when scrolling down (but not at the very top)
      else if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsHeaderVisible(false);
      }
      
      setLastScrollY(currentScrollY);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, [lastScrollY]);

  // Don't render theme-dependent content until mounted
  if (!mounted) {
    return <LoadingScreen message="Loading Commission Tracker..." />;
  }

  return (
    <div className={`min-h-screen ${isDark ? 'dark' : ''}`}>
      {/* Navigation */}
      <motion.nav 
        initial={{ y: 0 }}
        animate={{ y: isHeaderVisible ? 0 : -100 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md"
      >
        <div className="w-full max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center space-x-2 sm:space-x-3">
            <div className="w-6 h-6 sm:w-8 sm:h-8 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-lg flex items-center justify-center">
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
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-2 sm:space-x-4">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => router.push('/auth')}
                className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-3 py-1.5 sm:px-6 sm:py-2 rounded-lg text-sm sm:text-base font-semibold hover:from-blue-700 hover:to-purple-700 transition-all duration-200 cursor-pointer"
              >
                Sign In / Sign Up
              </motion.button>
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Toggle mobile menu"
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>

          {/* Mobile Menu */}
          <AnimatePresence>
            {isMobileMenuOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="md:hidden border-t border-slate-200 dark:border-slate-700 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md"
              >
                <div className="py-4 space-y-4">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      router.push('/auth');
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full mx-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-3 rounded-lg text-base font-semibold hover:from-blue-700 hover:to-purple-700 transition-all duration-200 cursor-pointer"
                  >
                    Sign In / Sign Up
                  </motion.button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.nav>

      {/* Unified Hero Section with all three parts */}
      <section className="relative bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 overflow-hidden">
        <HeroScrollStorytelling />
        {/* Hero Content */}
        <Hero onGetStarted={handleGetStarted} />
        {/* Company Carousel Content */}
        <CompanyCarousel />
        {/* Feature Grid Content */}
        <FeatureGrid />
        {/* Benefits Section */}
        <BenefitsSection />
        {/* In Action Section */}
        <StepScrollStorytelling />
      </section>

      {/* Use Case Showcase */}
      <UseCaseShowcase />

      {/* CTA Section */}
      <section className="py-16 sm:py-20 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600">
        <div className="w-full lg:w-[80%] mx-auto text-center px-4 sm:px-6 lg:px-8 xl:px-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl 2xl:text-5xl font-bold text-white mb-4 sm:mb-6">
              Ready to Transform Your Commission Tracking?
            </h2>
            <p className="text-lg sm:text-xl 2xl:text-xl text-blue-100 mb-6 sm:mb-8 max-w-3xl mx-auto">
              Join thousands of agents who have already revolutionized their commission management.
            </p>
            <div className="max-w-md mx-auto">
              <RegistrationForm onSubmit={handleGetStarted} />
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 dark:bg-slate-950 text-white py-8 sm:py-12">
        <div className="w-full max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-3 mb-4">
              <div className="w-6 h-6 sm:w-8 sm:h-8 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-lg flex items-center justify-center">
                <img 
                  src="/images/icon.svg" 
                  alt="Commission Tracker Icon" 
                  className="w-5 h-5 object-contain sm:w-5 sm:h-5 text-white"
                />
              </div>
              <div className="h-8 sm:h-10 lg:h-12 flex items-center">
                <img 
                  src="/images/logo-dark.svg" 
                  alt="Commission Tracker" 
                  className="h-full object-contain"
                />
              </div>
            </div>
          </div>
          
          {/* Testimonial Section */}
          <div className="border-t border-slate-800 mt-6 sm:mt-8 pt-6 sm:pt-8">
            <div className="text-center max-w-4xl mx-auto">
              <blockquote className="text-base sm:text-lg 2xl:text-lg text-slate-300 dark:text-slate-200 italic max-w-3xl mx-auto mb-4">
                &quot;Commission Tracker has revolutionized how we manage our commission data. The automation saves us hours every week.&quot;
              </blockquote>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-4">
                <div className="text-sm sm:text-base 2xl:text-base font-semibold text-slate-200 dark:text-slate-100">Sarah Johnson</div>
                <div className="text-xs sm:text-sm 2xl:text-sm text-slate-400 dark:text-slate-300">CEO, Premier Insurance Group</div>
              </div>
            </div>
          </div>
          
          <div className="border-t border-slate-800 mt-6 sm:mt-8 pt-6 sm:pt-8 flex flex-col sm:flex-row justify-between items-center gap-4">
            <p className="text-slate-400 text-sm sm:text-base text-center sm:text-left">&copy; 2025 Commission Tracker. All rights reserved.</p>
            <button
              onClick={() => setLandingTheme(actualTheme === 'dark' ? 'light' : 'dark')}
              className="flex items-center gap-2 px-3 py-2 sm:px-4 sm:py-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors text-slate-300 hover:text-white cursor-pointer text-sm sm:text-base"
              aria-label={`Switch to ${actualTheme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {actualTheme === 'dark' ? <Sun className="w-3 h-3 sm:w-4 sm:h-4" /> : <Moon className="w-3 h-3 sm:w-4 sm:h-4" />}
              <span className="text-xs sm:text-sm">
                {actualTheme === 'dark' ? 'Light Mode' : 'Dark Mode'}
              </span>
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
