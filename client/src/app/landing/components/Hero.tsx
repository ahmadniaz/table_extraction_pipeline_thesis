'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Play, CheckCircle, Star, Volume2 } from 'lucide-react';

interface HeroProps {
  onGetStarted: (email: string) => void;
}

export default function Hero({ onGetStarted }: HeroProps) {
  const [email, setEmail] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.trim()) {
      onGetStarted(email);
    }
  };

  const stats = [
    { value: '95%', label: 'Accuracy Rate' },
    { value: '10x', label: 'Faster Processing' },
    { value: '50+', label: 'Happy Customers' },
    { value: '24/7', label: 'Support' }
  ];

  const features = [
    'AI-Powered Extraction',
    'Multi-Format Support',
    'Real-time Processing',
    'Enterprise Security'
  ];

  return (
    <div className="relative w-full max-w-screen-2xl mx-auto py-12 sm:py-16 lg:py-20 px-4 sm:px-6 lg:px-8 xl:px-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 sm:gap-12 items-center">
          {/* Left Column - Content */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            className="space-y-8"
          >
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium"
            >
              <Star className="w-4 h-4 fill-current" />
              <span>Trusted by 50+ Companies</span>
            </motion.div>

            {/* Headline */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="space-y-3 sm:space-y-4"
            >
              <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl 2xl:text-7xl font-bold bg-gradient-to-r from-slate-900 via-slate-800 to-slate-700 dark:from-slate-100 dark:via-slate-200 dark:to-slate-300 bg-clip-text text-transparent leading-tight">
                Track Commissions
                <br />
                <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                  Like Never Before
                </span>
              </h1>
              <p className="text-lg sm:text-xl 2xl:text-xl text-slate-600 dark:text-slate-400 max-w-2xl">
                Automate commission statement processing, gain powerful insights, and streamline your financial tracking with our AI-powered platform.
              </p>
            </motion.div>

            {/* Features List */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.6 }}
              className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3"
            >
              {features.map((feature, index) => (
                <div key={index} className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 flex-shrink-0" />
                  <span className="text-sm sm:text-base text-slate-700 dark:text-slate-400 font-medium">{feature}</span>
                </div>
              ))}
            </motion.div>

            {/* CTA Form */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
              className="space-y-3 sm:space-y-4"
            >
              <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 sm:gap-4">
                <div className="flex-1 max-w-md">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email address"
                    className="w-full px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 text-sm sm:text-base"
                    required
                  />
                </div>
                <motion.button
                  type="submit"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-6 sm:px-8 py-2.5 sm:py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-semibold hover:from-blue-700 hover:to-purple-700 transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm sm:text-base"
                >
                  Get Started Free
                  <ArrowRight className="w-3 h-3 sm:w-4 sm:h-4" />
                </motion.button>
              </form>
              <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                No credit card required • 14-day free trial
              </p>
            </motion.div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 1.0 }}
              className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 pt-6 sm:pt-8 border-t border-slate-200 dark:border-slate-700"
            >
              {stats.map((stat, index) => (
                <div key={index} className="text-center">
                  <div className="text-xl sm:text-2xl 2xl:text-2xl font-bold text-slate-800 dark:text-slate-200">{stat.value}</div>
                  <div className="text-xs sm:text-sm 2xl:text-sm text-slate-600 dark:text-slate-400">{stat.label}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Right Column - Video */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative"
          >
            {/* Video Container */}
            <div className="relative bg-slate-100 dark:bg-slate-800 rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-700">
              {/* Video Placeholder */}
              <div className="aspect-video bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center relative">
                {/* Play Button Overlay */}
                <div className="absolute inset-0 flex items-center justify-center bg-slate-500/20 hover:bg-slate-500/30 dark:bg-black/30 dark:hover:bg-black/40 transition-colors">
                  <motion.button
                    className="w-20 h-20 bg-white/95 dark:bg-slate-700/95 rounded-full flex items-center justify-center border border-slate-300/50 dark:border-slate-600/20 cursor-pointer"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Play className="w-8 h-8 text-slate-700 dark:text-slate-100 ml-1" />
                  </motion.button>
                </div>

                {/* Controls */}
                <div className="absolute bottom-4 right-4 flex gap-2">
                  <motion.button
                    className="p-2 bg-slate-600/80 hover:bg-slate-700/90 dark:bg-slate-700/80 dark:hover:bg-slate-600/90 rounded-full text-white transition-colors cursor-pointer border border-slate-400/30 dark:border-slate-500/30"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                  >
                    <Volume2 className="w-4 h-4" />
                  </motion.button>
                </div>
              </div>
            </div>

            {/* Video Info */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="text-center mt-6"
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
                <Play className="w-4 h-4" />
                <span>2:30 min demo</span>
              </div>
              <p className="text-slate-600 dark:text-slate-400 mt-2 text-sm">
                See how easy it is to upload, process, and analyze your commission data
              </p>
            </motion.div>

          </motion.div>
        </div>
      </div>
  );
}
