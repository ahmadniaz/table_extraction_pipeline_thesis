'use client';

import React, { useRef, useEffect } from 'react';
import { Parallax, ParallaxLayer } from '@react-spring/parallax';
import { motion } from 'framer-motion';
import { FileText, FileSpreadsheet, CheckCircle, Mouse } from 'lucide-react';

const ScrollStorytellingCombined = () => {
  const parallaxRef = useRef<any>(null);

  useEffect(() => {
    if (parallaxRef.current) {
      parallaxRef.current.scrollTo(0);
    }
    
    // Agregar estilos globales para ocultar scrollbars
    const style = document.createElement('style');
    style.textContent = `
      .hero-parallax-container::-webkit-scrollbar {
        display: none !important;
      }
      .hero-parallax-container {
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
      }
    `;
    style.setAttribute('data-hero-parallax-hide-scrollbar', 'true');
    if (!document.head.querySelector('style[data-hero-parallax-hide-scrollbar]')) {
      document.head.appendChild(style);
    }
    
    return () => {
      const existingStyle = document.head.querySelector('style[data-hero-parallax-hide-scrollbar]');
      if (existingStyle) {
        existingStyle.remove();
      }
    };
  }, []);

  // Aplicar clase CSS al contenedor del parallax
  useEffect(() => {
    if (parallaxRef.current) {
      const container = parallaxRef.current.container.current;
      if (container) {
        container.classList.add('hero-parallax-container');
      }
    }
  }, []);

  return (
    <div className="relative w-full h-screen max-h-[1080px] overflow-hidden bg-white dark:bg-slate-900">
      <Parallax 
        ref={parallaxRef} 
        pages={2}
        style={{
          scrollbarWidth: 'none',
          msOverflowStyle: 'none'
        }}
      >
        
        {/* Title Section */}
        <ParallaxLayer offset={0} speed={0.1} className="flex justify-center">
          <motion.div
            initial={{ opacity: 0, y: 200 }}
            animate={{ opacity: 1, y: 100 }}
            transition={{ duration: 0.8 }}
            className="text-center z-10"
          >
            <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl 2k:text-7xl 4k:text-8xl 5k:text-9xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-3 sm:mb-4 md:mb-6 2k:mb-8 4k:mb-12 5k:mb-16 px-4">
              From Documents to Data
            </h2>
            <p className="text-base sm:text-lg md:text-xl lg:text-2xl 2k:text-3xl 4k:text-4xl 5k:text-5xl text-slate-600 dark:text-slate-300 max-w-2xl sm:max-w-3xl 2k:max-w-4xl 4k:max-w-5xl 5k:max-w-6xl mx-auto px-4">
              Watch how we transform your PDF statements and Excel files into actionable insights
            </p>
          </motion.div>
        </ParallaxLayer>

        {/* PDF File */}
        <ParallaxLayer offset={0.4} speed={-0.8} className="flex justify-center">
          <motion.div
            initial={{ x: -1000, opacity: 0, rotate: -15 }}
            animate={{ x: -150, opacity: 1, rotate: -5 }}
            transition={{ duration: 1.2, delay: 0.5 }}
            className="relative z-20"
          >
            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 sm:p-8 lg:p-10 2k:p-12 4k:p-14 5k:p-18 border-4 border-red-200 dark:border-red-700 max-w-md sm:max-w-lg lg:max-w-xl 2k:max-w-2xl 4k:max-w-3xl 5k:max-w-4xl w-[320px] sm:w-[380px] md:w-[420px] lg:w-[480px] xl:w-[520px] 2k:w-[600px] 4k:w-[700px] 5k:w-[800px]">
              {/* Header */}
              <div className="flex items-center space-x-2 sm:space-x-3 2k:space-x-4 4k:space-x-6 5k:space-x-8 mb-3 sm:mb-4 2k:mb-6 4k:mb-8 5k:mb-10">
                <div className="w-12 h-12 sm:w-14 sm:h-14 2k:w-18 2k:h-18 4k:w-22 4k:h-22 5k:w-26 5k:h-26 bg-red-500 rounded-lg flex items-center justify-center">
                  <FileText className="w-6 h-6 sm:w-7 sm:h-7 2k:w-9 2k:h-9 4k:w-11 4k:h-11 5k:w-13 5k:h-13 text-white" />
                </div>
                <div>
                  <h3 className="text-base sm:text-xl 2k:text-2xl 4k:text-3xl 5k:text-4xl font-bold text-slate-800 dark:text-slate-200">Commission Report</h3>
                  <p className="text-sm sm:text-base 2k:text-lg 4k:text-xl 5k:text-2xl text-slate-600 dark:text-slate-400">PDF Document</p>
                </div>
              </div>

              {/* Document Content */}
              <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-3 sm:p-4 lg:p-6 2k:p-8 4k:p-10 5k:p-12 space-y-2 sm:space-y-3 lg:space-y-4 2k:space-y-6 4k:space-y-8 5k:space-y-10">
                {/* Header */}
                <div className="text-center border-b border-slate-200 dark:border-slate-600 pb-2 sm:pb-3">
                  <h4 className="text-[10px] sm:text-sm lg:text-base 2k:text-lg 4k:text-xl 5k:text-2xl font-bold text-slate-800 dark:text-slate-200">COMMISSION STATEMENT</h4>
                  <p className="text-[9px] sm:text-sm 2k:text-base 4k:text-lg 5k:text-xl text-slate-600 dark:text-slate-400">Period: Oct 2025</p>
                </div>

                {/* Content Lines */}
                <div className="space-y-2 sm:space-y-3">
                  <div className="flex justify-between items-center">
                    <div className="h-3 sm:h-4 bg-slate-300 dark:bg-slate-600 rounded w-20 sm:w-24"></div>
                    <div className="h-3 sm:h-4 bg-green-400 rounded w-16 sm:w-20"></div>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="h-3 sm:h-4 bg-slate-300 dark:bg-slate-600 rounded w-24 sm:w-28"></div>
                    <div className="h-3 sm:h-4 bg-green-400 rounded w-20 sm:w-24"></div>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="h-3 sm:h-4 bg-slate-300 dark:bg-slate-600 rounded w-18 sm:w-22"></div>
                    <div className="h-3 sm:h-4 bg-green-400 rounded w-14 sm:w-18"></div>
                  </div>
                </div>

                {/* Total */}
                <div className="border-t border-slate-200 dark:border-slate-600 pt-2 sm:pt-3">
                  <div className="flex justify-between items-center">
                    <div className="h-4 sm:h-5 bg-slate-400 dark:bg-slate-500 rounded w-16 sm:w-20"></div>
                    <div className="h-4 sm:h-5 bg-green-500 rounded w-20 sm:w-24"></div>
                  </div>
                </div>
              </div>

              {/* File Info */}
              <div className="mt-3 sm:mt-4 flex items-center justify-between text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                <span>2.3 MB</span>
                <span>•</span>
                <span>3 pages</span>
              </div>
            </div>
          </motion.div>
        </ParallaxLayer>

        {/* Excel File */}
        <ParallaxLayer offset={0.4} speed={-0.8} className="flex justify-center">
          <motion.div
            initial={{ x: 1000, opacity: 0, rotate: 15 }}
            animate={{ x: 150, opacity: 1, rotate: 5 }}
            transition={{ duration: 1.2, delay: 0.5 }}
            className="relative z-20"
          >
            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 sm:p-8 lg:p-10 2k:p-12 4k:p-14 5k:p-18 border-4 border-green-200 dark:border-green-700 max-w-md sm:max-w-lg lg:max-w-xl 2k:max-w-2xl 4k:max-w-3xl 5k:max-w-4xl w-[320px] sm:w-[380px] md:w-[420px] lg:w-[480px] xl:w-[520px] 2k:w-[600px] 4k:w-[700px] 5k:w-[800px]">
              {/* Header */}
              <div className="flex items-center space-x-2 sm:space-x-3 2k:space-x-4 4k:space-x-6 5k:space-x-8 mb-3 sm:mb-4 2k:mb-6 4k:mb-8 5k:mb-10">
                <div className="w-12 h-12 sm:w-14 sm:h-14 2k:w-18 2k:h-18 4k:w-22 4k:h-22 5k:w-26 5k:h-26 bg-green-500 rounded-lg flex items-center justify-center">
                  <FileSpreadsheet className="w-6 h-6 sm:w-7 sm:h-7 2k:w-9 2k:h-9 4k:w-11 4k:h-11 5k:w-13 5k:h-13 text-white" />
                </div>
                <div>
                  <h3 className="text-base sm:text-xl 2k:text-2xl 4k:text-3xl 5k:text-4xl font-bold text-slate-800 dark:text-slate-200">Commission Data</h3>
                  <p className="text-sm sm:text-base 2k:text-lg 4k:text-xl 5k:text-2xl text-slate-600 dark:text-slate-400">Excel Spreadsheet</p>
                </div>
              </div>

              {/* Spreadsheet Content */}
              <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-2 sm:p-3 lg:p-4 2k:p-6 4k:p-8 5k:p-10">
                {/* Column Headers */}
                <div className="grid grid-cols-4 gap-2 sm:gap-3 mb-3 sm:mb-4">
                  <div className="h-6 sm:h-7 lg:h-8 bg-green-200 dark:bg-green-800 rounded text-xs sm:text-sm lg:text-base flex items-center justify-center font-bold text-green-800 dark:text-green-200">A</div>
                  <div className="h-6 sm:h-7 lg:h-8 bg-green-200 dark:bg-green-800 rounded text-xs sm:text-sm lg:text-base flex items-center justify-center font-bold text-green-800 dark:text-green-200">B</div>
                  <div className="h-6 sm:h-7 lg:h-8 bg-green-200 dark:bg-green-800 rounded text-xs sm:text-sm lg:text-base flex items-center justify-center font-bold text-green-800 dark:text-green-200">C</div>
                  <div className="h-6 sm:h-7 lg:h-8 bg-green-200 dark:bg-green-800 rounded text-xs sm:text-sm lg:text-base flex items-center justify-center font-bold text-green-800 dark:text-green-200">D</div>
                </div>

                {/* Row 1 - Headers */}
                <div className="grid grid-cols-4 gap-2 sm:gap-3 mb-3">
                  <div className="h-5 sm:h-6 lg:h-7 bg-blue-100 dark:bg-blue-900/30 rounded text-xs sm:text-sm lg:text-base flex items-center justify-center font-semibold text-blue-800 dark:text-blue-200">Agent</div>
                  <div className="h-5 sm:h-6 lg:h-7 bg-blue-100 dark:bg-blue-900/30 rounded text-xs sm:text-sm lg:text-base flex items-center justify-center font-semibold text-blue-800 dark:text-blue-200">Sales</div>
                  <div className="h-5 sm:h-6 lg:h-7 bg-blue-100 dark:bg-blue-900/30 rounded text-xs sm:text-sm lg:text-base flex items-center justify-center font-semibold text-blue-800 dark:text-blue-200">Rate</div>
                  <div className="h-5 sm:h-6 lg:h-7 bg-blue-100 dark:bg-blue-900/30 rounded text-xs sm:text-sm lg:text-base flex items-center justify-center font-semibold text-blue-800 dark:text-blue-200">Commission</div>
                </div>

                {/* Data Rows */}
                <div className="space-y-2 sm:space-y-3">
                  <div className="grid grid-cols-4 gap-2 sm:gap-3">
                    <div className="h-5 sm:h-6 bg-slate-200 dark:bg-slate-600 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-300 dark:bg-green-700 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-300 dark:bg-green-700 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-400 dark:bg-green-600 rounded"></div>
                  </div>
                  <div className="grid grid-cols-4 gap-2 sm:gap-3">
                    <div className="h-5 sm:h-6 bg-slate-200 dark:bg-slate-600 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-300 dark:bg-green-700 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-300 dark:bg-green-700 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-400 dark:bg-green-600 rounded"></div>
                  </div>
                  <div className="grid grid-cols-4 gap-2 sm:gap-3">
                    <div className="h-5 sm:h-6 bg-slate-200 dark:bg-slate-600 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-300 dark:bg-green-700 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-300 dark:bg-green-700 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-400 dark:bg-green-600 rounded"></div>
                  </div>
                </div>

                {/* Total Row */}
                <div className="border-t border-slate-300 dark:border-slate-600 mt-3 sm:mt-4 pt-2 sm:pt-3">
                  <div className="grid grid-cols-4 gap-2 sm:gap-3">
                    <div className="h-5 sm:h-6 bg-slate-300 dark:bg-slate-500 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-400 dark:bg-green-600 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-400 dark:bg-green-600 rounded"></div>
                    <div className="h-5 sm:h-6 bg-green-500 dark:bg-green-500 rounded"></div>
                  </div>
                </div>
              </div>

              {/* File Info */}
              <div className="mt-3 sm:mt-4 flex items-center justify-between text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                <span>1.8 MB</span>
                <span>•</span>
                <span>25 rows</span>
              </div>
            </div>
          </motion.div>
        </ParallaxLayer>

        {/* Merged Result */}
        <ParallaxLayer offset={1} speed={0.5} className="flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.5, y: 100 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 1, delay: 2 }}
            className="relative z-40 px-2 sm:px-4"
          >
            <div className="bg-white dark:bg-slate-800 rounded-2xl sm:rounded-3xl p-3 sm:p-4 lg:p-6 xl:p-8 2k:p-12 4k:p-16 5k:p-20 border-4 border-purple-200 dark:border-purple-700 max-w-xs sm:max-w-lg lg:max-w-2xl 2k:max-w-4xl 4k:max-w-5xl 5k:max-w-6xl w-full">
              {/* Header */}
              <div className="text-center mb-4 sm:mb-6 lg:mb-8">
                <div className="w-12 h-12 sm:w-16 sm:h-16 lg:w-20 lg:h-20 2k:w-24 2k:h-24 4k:w-28 4k:h-28 5k:w-32 5k:h-32 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-2xl sm:rounded-3xl flex items-center justify-center mx-auto mb-3 sm:mb-4 lg:mb-6 2k:mb-8 4k:mb-10 5k:mb-12">
                  <CheckCircle className="w-6 h-6 sm:w-8 sm:h-8 lg:w-10 lg:h-10 2k:w-12 2k:h-12 4k:w-14 4k:h-14 5k:w-16 5k:h-16 text-white" />
                </div>
                <h3 className="text-lg sm:text-xl lg:text-2xl 2k:text-3xl 4k:text-4xl 5k:text-5xl font-bold text-slate-800 dark:text-slate-200 mb-1 sm:mb-2 lg:mb-3 2k:mb-4 4k:mb-6 5k:mb-8">
                  Unified Dashboard
                </h3>
                <p className="text-xs sm:text-sm lg:text-lg 2k:text-xl 4k:text-2xl 5k:text-3xl text-slate-600 dark:text-slate-400">
                  AI-powered insights from multiple data sources
                </p>
              </div>
              
                {/* Dashboard Preview */}
                <div className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-700 dark:to-slate-800 rounded-2xl p-4 sm:p-6 2k:p-8 4k:p-10 5k:p-12 mb-4 sm:mb-6 2k:mb-8 4k:mb-10 5k:mb-12">

                {/* Document and Table */}
                <div className="bg-white dark:bg-slate-800 rounded-xl p-3 sm:p-4 2k:p-6 4k:p-8 5k:p-10">
                  <div className="flex items-center justify-between mb-3 sm:mb-4">
                    <h4 className="text-xs sm:text-sm 2k:text-base 4k:text-lg 5k:text-xl font-semibold text-slate-700 dark:text-slate-300">Data Processing</h4>
                    <div className="flex space-x-1 sm:space-x-2">
                      <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-blue-500 rounded-full"></div>
                      <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-green-500 rounded-full"></div>
                      <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-purple-500 rounded-full"></div>
                    </div>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4">
                    {/* Document Preview */}
                    <div className="flex-1">
                      <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-2 sm:p-3 border border-slate-200 dark:border-slate-600">
                        <div className="flex items-center space-x-2 mb-2 sm:mb-3">
                          <div className="w-5 h-5 sm:w-6 sm:h-6 bg-red-500 rounded flex items-center justify-center">
                            <FileText className="w-3 h-3 text-white" />
                          </div>
                          <span className="text-xs 2k:text-sm 4k:text-base 5k:text-lg font-medium text-slate-700 dark:text-slate-300">Commission Report.pdf</span>
                        </div>
                        
                        {/* Document Content */}
                        <div className="space-y-1 sm:space-y-2">
                          <div className="h-1.5 sm:h-2 bg-slate-300 dark:bg-slate-600 rounded w-3/4"></div>
                          <div className="h-1.5 sm:h-2 bg-slate-300 dark:bg-slate-600 rounded w-1/2"></div>
                          <div className="h-1.5 sm:h-2 bg-slate-300 dark:bg-slate-600 rounded w-5/6"></div>
                          <div className="h-1.5 sm:h-2 bg-slate-300 dark:bg-slate-600 rounded w-2/3"></div>
                        </div>
                        
                        <div className="mt-2 sm:mt-3 pt-1 sm:pt-2 border-t border-slate-200 dark:border-slate-600">
                          <div className="flex justify-between items-center">
                            <div className="h-1.5 sm:h-2 bg-slate-400 dark:bg-slate-500 rounded w-1/3"></div>
                            <div className="h-1.5 sm:h-2 bg-green-400 dark:bg-green-600 rounded w-1/4"></div>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Table Preview */}
                    <div className="flex-1">
                      <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-2 sm:p-3 border border-slate-200 dark:border-slate-600">
                        <div className="flex items-center space-x-2 mb-2 sm:mb-3">
                          <div className="w-5 h-5 sm:w-6 sm:h-6 bg-green-500 rounded flex items-center justify-center">
                            <FileSpreadsheet className="w-3 h-3 text-white" />
                          </div>
                          <span className="text-xs 2k:text-sm 4k:text-base 5k:text-lg font-medium text-slate-700 dark:text-slate-300">Extracted Data</span>
                        </div>
                        
                        {/* Table Content */}
                        <div className="space-y-1">
                          {/* Header Row */}
                          <div className="grid grid-cols-3 gap-1">
                            <div className="h-2 sm:h-2.5 bg-blue-200 dark:bg-blue-800 rounded text-[8px] sm:text-[10px] flex items-center justify-center font-medium text-blue-800 dark:text-blue-200">Agent</div>
                            <div className="h-2 sm:h-2.5 bg-blue-200 dark:bg-blue-800 rounded text-[8px] sm:text-[10px] flex items-center justify-center font-medium text-blue-800 dark:text-blue-200">Amount</div>
                            <div className="h-2 sm:h-2.5 bg-blue-200 dark:bg-blue-800 rounded text-[8px] sm:text-[10px] flex items-center justify-center font-medium text-blue-800 dark:text-blue-200">Commission</div>
                          </div>
                          
                          {/* Data Rows */}
                          <div className="space-y-1">
                            <div className="grid grid-cols-3 gap-1">
                              <div className="h-1.5 sm:h-2 bg-slate-300 dark:bg-slate-600 rounded"></div>
                              <div className="h-1.5 sm:h-2 bg-green-300 dark:bg-green-700 rounded"></div>
                              <div className="h-1.5 sm:h-2 bg-green-400 dark:bg-green-600 rounded"></div>
                            </div>
                            <div className="grid grid-cols-3 gap-1">
                              <div className="h-1.5 sm:h-2 bg-slate-300 dark:bg-slate-600 rounded"></div>
                              <div className="h-1.5 sm:h-2 bg-green-300 dark:bg-green-700 rounded"></div>
                              <div className="h-1.5 sm:h-2 bg-green-400 dark:bg-green-600 rounded"></div>
                            </div>
                            <div className="grid grid-cols-3 gap-1">
                              <div className="h-1.5 sm:h-2 bg-slate-300 dark:bg-slate-600 rounded"></div>
                              <div className="h-1.5 sm:h-2 bg-green-300 dark:bg-green-700 rounded"></div>
                              <div className="h-1.5 sm:h-2 bg-green-400 dark:bg-green-600 rounded"></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Features */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2k:grid-cols-3 4k:grid-cols-3 5k:grid-cols-3 gap-2 sm:gap-3 lg:gap-4 2k:gap-6 4k:gap-8 5k:gap-10">
                <div className="flex items-center space-x-2 sm:space-x-3 2k:space-x-4 4k:space-x-6 5k:space-x-8 p-2 sm:p-3 2k:p-4 4k:p-6 5k:p-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg sm:rounded-xl">
                  <div className="w-6 h-6 sm:w-8 sm:h-8 2k:w-10 2k:h-10 4k:w-12 4k:h-12 5k:w-14 5k:h-14 bg-blue-500 rounded-lg flex items-center justify-center">
                    <CheckCircle className="w-3 h-3 sm:w-4 sm:h-4 2k:w-5 2k:h-5 4k:w-6 4k:h-6 5k:w-7 5k:h-7 text-white" />
                  </div>
                  <div>
                    <p className="text-xs sm:text-sm 2k:text-base 4k:text-lg 5k:text-xl font-semibold text-blue-800 dark:text-blue-200">Auto Extraction</p>
                    <p className="text-[10px] sm:text-xs 2k:text-sm 4k:text-base 5k:text-lg text-blue-600 dark:text-blue-400">Smart data parsing</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 sm:space-x-3 2k:space-x-4 4k:space-x-6 5k:space-x-8 p-2 sm:p-3 2k:p-4 4k:p-6 5k:p-8 bg-green-50 dark:bg-green-900/20 rounded-lg sm:rounded-xl">
                  <div className="w-6 h-6 sm:w-8 sm:h-8 2k:w-10 2k:h-10 4k:w-12 4k:h-12 5k:w-14 5k:h-14 bg-green-500 rounded-lg flex items-center justify-center">
                    <CheckCircle className="w-3 h-3 sm:w-4 sm:h-4 2k:w-5 2k:h-5 4k:w-6 4k:h-6 5k:w-7 5k:h-7 text-white" />
                  </div>
                  <div>
                    <p className="text-xs sm:text-sm 2k:text-base 4k:text-lg 5k:text-xl font-semibold text-green-800 dark:text-green-200">Real-time Analytics</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 sm:space-x-3 2k:space-x-4 4k:space-x-6 5k:space-x-8 p-2 sm:p-3 2k:p-4 4k:p-6 5k:p-8 bg-purple-50 dark:bg-purple-900/20 rounded-lg sm:rounded-xl">
                  <div className="w-6 h-6 sm:w-8 sm:h-8 2k:w-10 2k:h-10 4k:w-12 4k:h-12 5k:w-14 5k:h-14 bg-purple-500 rounded-lg flex items-center justify-center">
                    <CheckCircle className="w-3 h-3 sm:w-4 sm:h-4 2k:w-5 2k:h-5 4k:w-6 4k:h-6 5k:w-7 5k:h-7 text-white" />
                  </div>
                  <div>
                    <p className="text-xs sm:text-sm 2k:text-base 4k:text-lg 5k:text-xl font-semibold text-purple-800 dark:text-purple-200">Smart Insights</p>
                    <p className="text-[10px] sm:text-xs 2k:text-sm 4k:text-base 5k:text-lg text-purple-600 dark:text-purple-400">AI-powered trends</p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </ParallaxLayer>

        {/* Scroll Indicator */}
        <ParallaxLayer offset={0.3} speed={0.2} className="flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.5 }}
            className="text-center"
          >
        <div className="flex flex-col items-center space-y-4">
          <Mouse className="w-12 h-12 2k:w-16 2k:h-16 4k:w-20 4k:h-20 5k:w-24 5k:h-24 text-transparent bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text animate-bounce" />

            </div>
          </motion.div>
        </ParallaxLayer>


      </Parallax>
    </div>
  );
};

export default ScrollStorytellingCombined;