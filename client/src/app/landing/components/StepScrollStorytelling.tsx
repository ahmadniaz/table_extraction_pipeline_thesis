'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Parallax, ParallaxLayer } from '@react-spring/parallax';
import { motion } from 'framer-motion';
import { Upload, Brain, BarChart3, FileText, FileSpreadsheet, CheckCircle, Database } from 'lucide-react';
import { useSectionVisibility } from '@/hooks/useSectionVisibility';

export default function InAction() {
    const [currentStep, setCurrentStep] = useState(0);
    const [isStorytellingActive, setIsStorytellingActive] = useState(false);
    const [isAdjusting, setIsAdjusting] = useState(false);
    const [isManualNavigation, setIsManualNavigation] = useState(false);
    const [parallaxProgress, setParallaxProgress] = useState(0);
    const parallaxRef = useRef<any>(null);
    
    // Hook personalizado para detectar visibilidad
    const {
        sectionRef,
        isFullyVisible,
        scrollProgress,
        isIntersecting,
        intersectionRatio
    } = useSectionVisibility({
        threshold: 1.0, // 100% visible
        rootMargin: '0px',
        debug: false // Cambiar a false en producción
    });

    useEffect(() => {
        if (parallaxRef.current) {
            parallaxRef.current.scrollTo(0);
        }
        
        // Agregar estilos globales para ocultar scrollbars
        const style = document.createElement('style');
        style.textContent = `
            .parallax-container::-webkit-scrollbar {
                display: none !important;
            }
            .parallax-container {
                scrollbar-width: none !important;
                -ms-overflow-style: none !important;
            }
        `;
        style.setAttribute('data-parallax-hide-scrollbar', 'true');
        if (!document.head.querySelector('style[data-parallax-hide-scrollbar]')) {
            document.head.appendChild(style);
        }
        
        return () => {
            const existingStyle = document.head.querySelector('style[data-parallax-hide-scrollbar]');
            if (existingStyle) {
                existingStyle.remove();
            }
        };
    }, []);

    // Track parallax scroll progress
    useEffect(() => {
        if (!parallaxRef.current) return;
        
        const container = parallaxRef.current.container.current;
        if (!container) return;

        const handleScroll = () => {
            if (container.scrollTop === 0) {
                setParallaxProgress(0);
            } else {
                const maxScroll = container.scrollHeight - container.clientHeight;
                const progress = (container.scrollTop / maxScroll) * 100;
                setParallaxProgress(Math.min(progress, 100));
            }
        };

        container.addEventListener('scroll', handleScroll);
        return () => container.removeEventListener('scroll', handleScroll);
    }, [isStorytellingActive]);


    // Activar scroll storytelling solo cuando scroll progress esté entre 95-100%
    useEffect(() => {
        // No hacer ajustes automáticos si estamos navegando manualmente
        if (isManualNavigation) return;
        
        if (scrollProgress >= 70) {
            setIsStorytellingActive(true);
            
            // Ajustar automáticamente para que ocupe el 100% de la pantalla
            if (scrollProgress < 100 && sectionRef.current && !isAdjusting) {
                setIsAdjusting(true);
                sectionRef.current.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start',
                    inline: 'nearest'
                });
                
                // Resetear el flag después de un tiempo
                setTimeout(() => {
                    setIsAdjusting(false);
                }, 1000);
            }
        } else {
            setIsStorytellingActive(false);
            // NO resetear - mantener el paso actual
        }
    }, [scrollProgress, isAdjusting, isManualNavigation]);

    // Controlar el scroll del parallax basado en el estado activo
    useEffect(() => {
        if (!parallaxRef.current) return;
        const container = parallaxRef.current.container.current;
        if (!container) return;

        if (isStorytellingActive) {
            // Habilitar scroll cuando está activo pero ocultar la barra
            container.style.overflow = 'auto';
            container.style.pointerEvents = 'auto';
            container.classList.add('parallax-container');
            console.log('🎬 Parallax scroll habilitado (barra oculta)');
        } else {
            // Deshabilitar scroll cuando no está activo
            container.style.overflow = 'hidden';
            container.style.pointerEvents = 'none';
            container.classList.remove('parallax-container');
            console.log('⏸️ Parallax scroll deshabilitado');
        }
    }, [isStorytellingActive]);

    // Scroll detection for steps - solo cuando storytelling está activo
    useEffect(() => {
        if (!parallaxRef.current) return;
        const container = parallaxRef.current.container.current;
        if (!container) return;

        const handleScroll = (e: Event) => {
            // No detectar cambios automáticos si estamos navegando manualmente
            if (isManualNavigation) return;
            
            // Solo detectar cambios de paso cuando storytelling esté activo
            if (!isStorytellingActive) {
                // No prevenir el scroll, solo no detectar cambios automáticos
                return;
            }

            const scrollTop = container.scrollTop;
            const maxScroll = container.scrollHeight - container.clientHeight;
            const scrollPercent = scrollTop / maxScroll;

            if (scrollPercent < 0.33) setCurrentStep(0);
            else if (scrollPercent < 0.66) setCurrentStep(1);
            else setCurrentStep(2);
        };

        container.addEventListener("scroll", handleScroll, { passive: true });
        return () => container.removeEventListener("scroll", handleScroll);
    }, [isStorytellingActive, isManualNavigation]);

    // Función para cambiar de paso manualmente
    const goToStep = (step: number) => {
        if (parallaxRef.current && step >= 0 && step <= 2) {
            // Marcar que estamos navegando manualmente
            setIsManualNavigation(true);
            
            // Cambiar el paso actual inmediatamente
            setCurrentStep(step);
            
            // Ir al step seleccionado en el parallax
            parallaxRef.current.scrollTo(step);
            
            // Desactivar la navegación manual después de un delay
            setTimeout(() => {
                setIsManualNavigation(false);
            }, 1000);
        }
    };


    // Step content
    const getStepContent = () => {
        const steps = [
            {
                title: "Upload",
                description: "Drag and drop your commission statements and Excel files. Our platform supports multiple formats for seamless data import with PDF and Excel support, and easy drag & drop functionality for effortless file uploads.",
                content: (stepTitle: string, stepDescription: string) => (
                    <div className="space-y-6">
                        {/* Animated Upload Demo */}
                        <div className="relative">
                            {/* Upload Zone with Animation */}
                            <motion.div
                                initial={{ scale: 0.95, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ duration: 0.6, delay: 0.2 }}
                                className="border-2 border-dashed border-blue-300 dark:border-blue-600 rounded-xl p-8 text-center bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 relative overflow-hidden"
                            >

                                {/* Upload Icon */}
                                <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                                    <Upload className="w-10 h-10 text-white" />
                                </div>

                                {/* Animated Text with PDF and Excel on sides */}
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.4 }}
                                    className="flex flex-col lg:flex-row items-center justify-center space-y-6 lg:space-y-0 lg:space-x-8 mb-4"
                                >
                                    {/* PDF File Preview */}
                                    <motion.div
                                        initial={{ x: -50, opacity: 0, rotate: -5 }}
                                        animate={{ x: 0, opacity: 1, rotate: -1 }}
                                        transition={{ duration: 0.8, delay: 1.7 }}
                                        className="bg-white dark:bg-slate-800 rounded-2xl p-4 sm:p-5 lg:p-6 border-4 border-red-200 dark:border-red-700 w-[192px] sm:w-[228px] md:w-[252px] lg:w-[288px] xl:w-[312px] cursor-pointer"
                                    >
                                        <div className="flex items-center space-x-2 sm:space-x-3 mb-3 sm:mb-4">
                                            <div className="w-8 h-8 sm:w-9 sm:h-9 bg-red-500 rounded-lg flex items-center justify-center">
                                                <FileText className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                                            </div>
                                            <div>
                                                <h4 className="text-sm sm:text-base font-bold text-slate-800 dark:text-slate-200">Commission Report</h4>
                                                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">PDF Document</p>
                                            </div>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-3 space-y-2">
                                            <div className="text-center border-b border-slate-200 dark:border-slate-600 pb-1">
                                                <h5 className="text-xs font-bold text-slate-800 dark:text-slate-200">COMMISSION STATEMENT</h5>
                                                <p className="text-xs text-slate-600 dark:text-slate-400">Period: Oct 2025</p>
                                            </div>
                                            <div className="space-y-1">
                                                <div className="flex justify-between items-center">
                                                    <div className="h-2 bg-slate-300 dark:bg-slate-600 rounded w-12"></div>
                                                    <div className="h-2 bg-green-400 rounded w-8"></div>
                                                </div>
                                                <div className="flex justify-between items-center">
                                                    <div className="h-2 bg-slate-300 dark:bg-slate-600 rounded w-16"></div>
                                                    <div className="h-2 bg-green-400 rounded w-12"></div>
                                                </div>
                                            </div>
                                            <div className="border-t border-slate-200 dark:border-slate-600 pt-1">
                                                <div className="flex justify-between items-center">
                                                    <div className="h-2 bg-slate-400 dark:bg-slate-500 rounded w-8"></div>
                                                    <div className="h-2 bg-green-500 rounded w-12"></div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="mt-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                                            <span>2.3 MB</span>
                                            <span>•</span>
                                            <span>3 pages</span>
                                        </div>
                                    </motion.div>

                                    {/* Excel File Preview */}
                                    <motion.div
                                        initial={{ x: 50, opacity: 0, rotate: 5 }}
                                        animate={{ x: 0, opacity: 1, rotate: 1 }}
                                        transition={{ duration: 0.8, delay: 1.9 }}
                                        className="bg-white dark:bg-slate-800 rounded-2xl p-4 sm:p-5 lg:p-6 border-4 border-green-200 dark:border-green-700 w-[192px] sm:w-[228px] md:w-[252px] lg:w-[288px] xl:w-[312px] cursor-pointer"
                                    >
                                        <div className="flex items-center space-x-2 sm:space-x-3 mb-3 sm:mb-4">
                                            <div className="w-8 h-8 sm:w-9 sm:h-9 bg-green-500 rounded-lg flex items-center justify-center">
                                                <FileSpreadsheet className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                                            </div>
                                            <div>
                                                <h4 className="text-sm sm:text-base font-bold text-slate-800 dark:text-slate-200">Commission Data</h4>
                                                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Excel Spreadsheet</p>
                                            </div>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-3 space-y-2">
                                            <div className="grid grid-cols-4 gap-1 mb-1">
                                                <div className="h-4 bg-green-200 dark:bg-green-800 rounded text-xs flex items-center justify-center font-bold text-green-800 dark:text-green-200">A</div>
                                                <div className="h-4 bg-green-200 dark:bg-green-800 rounded text-xs flex items-center justify-center font-bold text-green-800 dark:text-green-200">B</div>
                                                <div className="h-4 bg-green-200 dark:bg-green-800 rounded text-xs flex items-center justify-center font-bold text-green-800 dark:text-green-200">C</div>
                                                <div className="h-4 bg-green-200 dark:bg-green-800 rounded text-xs flex items-center justify-center font-bold text-green-800 dark:text-green-200">D</div>
                                            </div>
                                            <div className="grid grid-cols-4 gap-1 mb-1">
                                                <div className="h-3 bg-blue-100 dark:bg-blue-900/30 rounded text-xs flex items-center justify-center font-semibold text-blue-800 dark:text-blue-200"></div>
                                                <div className="h-3 bg-blue-100 dark:bg-blue-900/30 rounded text-xs flex items-center justify-center font-semibold text-blue-800 dark:text-blue-200"></div>
                                                <div className="h-3 bg-blue-100 dark:bg-blue-900/30 rounded text-xs flex items-center justify-center font-semibold text-blue-800 dark:text-blue-200"></div>
                                                <div className="h-3 bg-blue-100 dark:bg-blue-900/30 rounded text-xs flex items-center justify-center font-semibold text-blue-800 dark:text-blue-200"></div>
                                            </div>
                                            <div className="space-y-1">
                                                <div className="grid grid-cols-4 gap-1">
                                                    <div className="h-3 bg-slate-200 dark:bg-slate-600 rounded"></div>
                                                    <div className="h-3 bg-green-300 dark:bg-green-700 rounded"></div>
                                                    <div className="h-3 bg-green-300 dark:bg-green-700 rounded"></div>
                                                    <div className="h-3 bg-green-400 dark:bg-green-600 rounded"></div>
                                                </div>
                                                <div className="grid grid-cols-4 gap-1">
                                                    <div className="h-3 bg-slate-200 dark:bg-slate-600 rounded"></div>
                                                    <div className="h-3 bg-green-300 dark:bg-green-700 rounded"></div>
                                                    <div className="h-3 bg-green-300 dark:bg-green-700 rounded"></div>
                                                    <div className="h-3 bg-green-400 dark:bg-green-600 rounded"></div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="mt-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                                            <span>1.8 MB</span>
                                            <span>•</span>
                                            <span>25 rows</span>
                                        </div>
                                    </motion.div>
                                </motion.div>

                                {/* Footer Text - Drop your files here */}
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.6 }}
                                    className="text-center mt-6"
                                >
                                    <h4 className="text-lg font-bold text-blue-800 dark:text-blue-200 mb-2">
                                        Drop your files here
                                    </h4>
                                    <p className="text-sm text-blue-600 dark:text-blue-400">
                                        PDF or Excel files supported
                                    </p>
                                </motion.div>

                            </motion.div>


                            {/* Processing Animation Preview */}
                            <motion.div
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: 1.2 }}
                                className="mt-6 p-4 bg-slate-100 dark:bg-slate-800 rounded-lg"
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                        Processing Preview
                                    </span>
                                    <motion.div
                                        animate={{ rotate: 360 }}
                                        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                        className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"
                                    />
                                </div>

                                {/* Animated Progress Bar */}
                                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                                    <motion.div
                                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full"
                                        initial={{ width: "0%" }}
                                        animate={{ width: "75%" }}
                                        transition={{ duration: 3, ease: "easeInOut" }}
                                    />
                                </div>
                            </motion.div>

                        </div>
                    </div>
                )
            },
            {
                title: "AI Extraction",
                description: "Our AI engine analyzes each document, identifies patterns and extracts commission data with 98.5% accuracy through smart AI processing for intelligent data extraction and industry-leading precision for reliable results.",
                content: (stepTitle: string, stepDescription: string) => (
                    <div className="space-y-4">
                        {/* AI Processing Demo */}
                        <div className="relative">

                            {/* Data Processing Section - Added from ScrollStorytellingCombined */}
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0 }}
                                className="mt-8 bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700"
                            >
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center space-x-3">
                                        <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                                            <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">Data Processing</h3>
                                            <p className="text-sm text-slate-600 dark:text-slate-400">Real-time extraction and validation</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                            AI Processing Data
                                        </span>
                                        <motion.div
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                            className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"
                                        />
                                    </div>
                                </div>

                                <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4">
                                    {/* Document Preview */}
                                    <motion.div
                                        initial={{ x: -20, opacity: 0 }}
                                        animate={{ x: 0, opacity: 1 }}
                                        transition={{ delay: 0.2 }}
                                        className="flex-1"
                                    >
                                        <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4 sm:p-6 border border-slate-200 dark:border-slate-600 min-h-[200px]">
                                            <div className="flex items-center space-x-2 mb-4">
                                                <div className="w-6 h-6 bg-red-500 rounded flex items-center justify-center">
                                                    <FileText className="w-4 h-4 text-white" />
                                                </div>
                                                <div>
                                                    <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Commission Report</span>
                                                    <p className="text-xs text-slate-500 dark:text-slate-400">Source Document</p>
                                                </div>
                                            </div>
                                            
                                            {/* Document Content with Carrier Detection */}
                                            <div className="space-y-3">
                                                <div className="h-3 bg-slate-300 dark:bg-slate-600 rounded w-full"></div>
                                                <div className="h-3 bg-slate-300 dark:bg-slate-600 rounded w-4/5"></div>
                                                <div className="h-3 bg-slate-300 dark:bg-slate-600 rounded w-3/4"></div>
                                                <div className="h-3 bg-slate-300 dark:bg-slate-600 rounded w-5/6"></div>
                                                <div className="h-3 bg-slate-300 dark:bg-slate-600 rounded w-2/3"></div>
                                            </div>
                                            
                                            {/* Document Analysis Info */}
                                            <div className="mt-3 pt-2 border-t border-slate-200 dark:border-slate-600">
                                                <div className="grid grid-cols-2 gap-2 mb-2">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Carrier:</span>
                                                        <div className="flex items-center space-x-1">
                                                            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                                                            <span className="text-xs text-green-600 dark:text-green-400">Blue Cross</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Date Range:</span>
                                                    <span className="text-xs text-slate-600 dark:text-slate-400">Jan 2024</span>
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                    
                                    {/* Table Preview */}
                                    <motion.div
                                        initial={{ x: 20, opacity: 0 }}
                                        animate={{ x: 0, opacity: 1 }}
                                        transition={{ delay: 1 }}
                                        className="flex-1"
                                    >
                                        <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4 sm:p-6 border border-slate-200 dark:border-slate-600 min-h-[200px]">
                                            <div className="flex items-center space-x-2 mb-4">
                                                <div className="w-6 h-6 bg-green-500 rounded flex items-center justify-center">
                                                    <FileSpreadsheet className="w-4 h-4 text-white" />
                                                </div>
                                                <div>
                                                    <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Extracted Data</span>
                                                    <p className="text-xs text-slate-500 dark:text-slate-400">Structured Table</p>
                                                </div>
                                            </div>
                                            
                                            {/* Table Content */}
                                            <div className="space-y-3">
                                                {/* Header Row */}
                                                <div className="grid grid-cols-4 gap-2">
                                                    <div className="h-4 bg-blue-200 dark:bg-blue-800 rounded text-[9px] flex items-center justify-center font-medium text-blue-800 dark:text-blue-200">Agent</div>
                                                    <div className="h-4 bg-blue-200 dark:bg-blue-800 rounded text-[9px] flex items-center justify-center font-medium text-blue-800 dark:text-blue-200">Amount</div>
                                                    <div className="h-4 bg-blue-200 dark:bg-blue-800 rounded text-[9px] flex items-center justify-center font-medium text-blue-800 dark:text-blue-200">Commission</div>
                                                    <div className="h-4 bg-blue-200 dark:bg-blue-800 rounded text-[9px] flex items-center justify-center font-medium text-blue-800 dark:text-blue-200">Date</div>
                                                </div>
                                                
                                                {/* Data Rows */}
                                                <div className="space-y-2">
                                                    <div className="grid grid-cols-4 gap-2">
                                                        <div className="h-3 bg-slate-300 dark:bg-slate-600 rounded"></div>
                                                        <div className="h-3 bg-green-300 dark:bg-green-700 rounded"></div>
                                                        <div className="h-3 bg-green-400 dark:bg-green-600 rounded"></div>
                                                        <div className="h-3 bg-purple-300 dark:bg-purple-700 rounded"></div>
                                                    </div>
                                                    <div className="grid grid-cols-4 gap-2">
                                                        <div className="h-3 bg-slate-300 dark:bg-slate-600 rounded"></div>
                                                        <div className="h-3 bg-green-300 dark:bg-green-700 rounded"></div>
                                                        <div className="h-3 bg-green-400 dark:bg-green-600 rounded"></div>
                                                        <div className="h-3 bg-purple-300 dark:bg-purple-700 rounded"></div>
                                                    </div>
                                                    <div className="grid grid-cols-4 gap-2">
                                                        <div className="h-3 bg-slate-300 dark:bg-slate-600 rounded"></div>
                                                        <div className="h-3 bg-green-300 dark:bg-green-700 rounded"></div>
                                                        <div className="h-3 bg-green-400 dark:bg-green-600 rounded"></div>
                                                        <div className="h-3 bg-purple-300 dark:bg-purple-700 rounded"></div>
                                                    </div>
                                                </div>
                                            </div>
                                            
                                            {/* Extraction Stats */}
                                            <div className="mt-3 pt-2 border-t border-slate-200 dark:border-slate-600">
                                                <div className="grid grid-cols-2 gap-2 mb-2">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Tables:</span>
                                                        <span className="text-xs text-blue-600 dark:text-blue-400">3 detected</span>
                                                    </div>
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Rows:</span>
                                                        <span className="text-xs text-slate-600 dark:text-slate-400">12 entries</span>
                                                    </div>
                                                </div>
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Column Mapping:</span>
                                                    <span className="text-xs text-green-600 dark:text-green-400">Auto-detected</span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Total Commission:</span>
                                                    <span className="text-xs text-green-600 dark:text-green-400">$2,450.00</span>
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                </div>
                            </motion.div>

                            {/* Accuracy Display */}
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 1 }}
                                className="mt-4 flex items-center justify-center space-x-2"
                            >
                                <CheckCircle className="w-4 h-4 text-green-500" />
                                <span className="text-sm text-green-600 dark:text-green-400">
                                    98.5% Accuracy
                                </span>
                            </motion.div>
                        </div>
                    </div>
                )
            },
            {
                title: "Statistics",
                description: "View comprehensive analytics and insights. Track performance, identify trends, and make data-driven decisions with real-time analytics for live data insights and performance tracking to monitor trends effectively.",
                content: (stepTitle: string, stepDescription: string) => (
                    <div className="space-y-6">
                        {/* Animated Dashboard Demo */}
                        <div className="relative">
                            {/* Main Dashboard Container */}
                            <motion.div
                                initial={{ scale: 0.95, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ duration: 0.6, delay: 0.2 }}
                                className="p-6 relative overflow-hidden"
                            >

                                {/* Dashboard Header */}
                                <motion.div
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.4 }}
                                    className="flex items-center justify-between mb-6"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                                            <Database className="w-6 h-6 text-white" />
                                        </div>
                                        <span className="font-bold text-slate-800 dark:text-slate-200 text-lg">Commission Tracker</span>
                                    </div>
                                </motion.div>

                                {/* Animated Stats Cards */}
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.6 }}
                                    className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6"
                                >
                                    <motion.div
                                        whileHover={{ scale: 1.05, y: -2 }}
                                        className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800"
                                    >
                                        <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                                            $45,230
                                        </div>
                                        <div className="text-sm text-blue-600 dark:text-blue-400 font-medium">Total Commissions</div>
                                    </motion.div>

                                    <motion.div
                                        whileHover={{ scale: 1.05, y: -2 }}
                                        className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 p-4 rounded-lg border border-green-200 dark:border-green-800"
                                    >
                                        <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                                            +12.5%
                                        </div>
                                        <div className="text-sm text-green-600 dark:text-green-400 font-medium">Growth</div>
                                    </motion.div>
                                </motion.div>

                                {/* Animated Chart */}
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.8 }}
                                    className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-700/50 dark:to-slate-600/50 rounded-xl p-6 border border-slate-200 dark:border-slate-600"
                                >
                                    <div className="flex items-center justify-between mb-6">
                                        <div>
                                            <span className="text-lg font-bold text-slate-700 dark:text-slate-300">
                                                Commission Trends
                                            </span>
                                            <p className="text-sm text-slate-500 dark:text-slate-400">Monthly Performance</p>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-2xl font-bold text-green-600 dark:text-green-400">+24%</div>
                                            <div className="text-xs text-slate-500 dark:text-slate-400">vs last month</div>
                                        </div>
                                    </div>

                                    {/* Enhanced Animated Bar Chart */}
                                    <div className="h-32 flex items-end justify-between space-x-1">
                                        {Array.from({ length: 12 }).map((_, i) => {
                                            const heights = [35, 55, 70, 45, 75, 95, 40, 60, 80, 50, 90, 65];
                                            const maxHeight = heights[i];
                                            const isHighValue = maxHeight > 70;
                                            return (
                                                <motion.div
                                                    key={i}
                                                    initial={{ height: 0 }}
                                                    animate={{
                                                        height: [5, maxHeight, 5]
                                                    }}
                                                    transition={{
                                                        duration: 3,
                                                        delay: i * 0.15,
                                                        repeat: Infinity,
                                                        ease: "easeInOut"
                                                    }}
                                                    className={`w-6 ${
                                                        isHighValue 
                                                            ? 'bg-gradient-to-t from-green-500 to-green-400' 
                                                            : 'bg-gradient-to-t from-blue-500 to-blue-400'
                                                    } shadow-sm`}
                                                />
                                            );
                                        })}
                                    </div>

                                    {/* Enhanced Chart Labels */}
                                    <div className="flex justify-between mt-4 text-xs text-slate-500 dark:text-slate-400">
                                        <span className="font-medium">Jan</span>
                                        <span className="font-medium">Mar</span>
                                        <span className="font-medium">May</span>
                                        <span className="font-medium">Jul</span>
                                        <span className="font-medium">Sep</span>
                                        <span className="font-medium">Nov</span>
                                    </div>

                                    {/* Chart Legend */}
                                    <div className="flex items-center justify-center space-x-4 mt-4 pt-4 border-t border-slate-200 dark:border-slate-600">
                                        <div className="flex items-center space-x-2">
                                            <div className="w-3 h-3 bg-green-500 rounded"></div>
                                            <span className="text-xs text-slate-600 dark:text-slate-400">High Performance</span>
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            <div className="w-3 h-3 bg-blue-500 rounded"></div>
                                            <span className="text-xs text-slate-600 dark:text-slate-400">Standard</span>
                                        </div>
                                    </div>
                                </motion.div>

                            </motion.div>

                        </div>
                    </div>
                )
            }
        ];

        return steps[currentStep] || steps[0];
    };

    const currentStepData = getStepContent();

    return (
        <div 
            ref={sectionRef}
            className="relative w-full max-w-screen-2xl h-screen mx-auto py-12 sm:py-16 lg:py-20 px-4 sm:px-6 lg:px-8 xl:px-12 overflow-hidden flex items-center justify-center"
            style={{ direction: 'rtl' }}
        >
            <Parallax 
                ref={parallaxRef} 
                pages={3}
                style={{
                    scrollbarWidth: 'none',
                    msOverflowStyle: 'none',
                    height: '100vh',
                    width: '100%'
                }}
            >
                {/* Sticky Content - Presente en todas las páginas */}
                <ParallaxLayer offset={0} speed={0} sticky={{ start: 0, end: 3 }} className="flex flex-col lg:flex-row items-center justify-end w-full" style={{ direction: 'ltr', height: '100vh' }}>
                    {/* Mobile Header - Visible only on small screens */}
                    <div className="lg:hidden w-full px-4 py-6 text-center">
                        <motion.div
                            initial={{ opacity: 0, y: -20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.8, delay: 0.1 }}
                            className="space-y-4"
                        >
                            <h2 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                                See Commission Tracker in Action
                            </h2>
                            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 leading-relaxed">
                                Watch how our platform transforms commission management in just a few minutes
                            </p>
                        </motion.div>
                    </div>

                    {/* Mobile Step Navigation - Visible only on small screens */}
                    <div className="lg:hidden w-full px-4 mb-4">
                        <div className="flex justify-center space-x-2">
                            {[0, 1, 2].map((step) => (
                                <button
                                    key={step}
                                    onClick={() => goToStep(step)}
                                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-300 cursor-pointer ${
                                        currentStep === step
                                            ? 'bg-blue-500 text-white'
                                            : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-300 dark:hover:bg-slate-600'
                                    }`}
                                >
                                    {step === 0 ? 'Upload' : step === 1 ? 'AI Extract' : 'Stats'}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Left: Clean Content Display - Desktop only */}
                    <div className="hidden lg:block w-2/5 pl-8 flex justify-center">
                        <motion.div
                            initial={{ opacity: 0, x: 50 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.8, delay: 0.1 }}
                            className="space-y-6 w-full max-w-2xl"
                        >
                            {/* Main Title and Subtitle */}
                            <div className="mb-6">
                                <h2 className="text-2xl sm:text-3xl lg:text-4xl xl:text-5xl 2xl:text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-3">
                                    See Commission Tracker in Action
                                </h2>
                                <p className="text-sm sm:text-base lg:text-lg xl:text-xl 2xl:text-xl text-slate-600 dark:text-slate-300 leading-relaxed">
                                    Watch how our platform transforms commission management in just a few minutes
                                </p>
                            </div>

                            {/* Fixed Steps */}
                            <div className="relative">
                                {/* Progress Line Container */}
                                <div className="absolute left-0 top-0 bottom-0 w-1 bg-slate-200 dark:bg-slate-700 rounded-full">
                                    {/* Progress Line */}
                                    <motion.div 
                                        className="w-full bg-gradient-to-b from-blue-500 to-purple-500 rounded-full"
                                        style={{
                                            height: `${parallaxProgress}%`
                                        }}
                                        transition={{ duration: 0.1, ease: "linear" }}
                                    />
                                </div>
                                
                                {/* Steps Container */}
                                <div className="pl-6 space-y-4">
                                    {[
                                        {
                                            title: "Upload",
                                            description: "Drag and drop your commission statements and Excel files. Our platform supports multiple formats for seamless data import with multiple file format support for PDF and Excel files, and easy drag & drop functionality for effortless file uploads.",
                                            icon: Upload,
                                            features: []
                                        },
                                        {
                                            title: "AI Extraction",
                                            description: "Our AI engine analyzes each document, identifies patterns and extracts commission data with 98.5% accuracy through smart AI processing for intelligent data extraction and industry-leading precision for reliable results.",
                                            icon: Brain,
                                            features: []
                                        },
                                        {
                                            title: "Statistics",
                                            description: "View comprehensive analytics and insights. Track performance, identify trends, and make data-driven decisions with real-time analytics for live insights and smart AI-powered trend analysis for comprehensive data intelligence.",
                                            icon: BarChart3,
                                            features: []
                                        }
                                    ].map((step, index) => (
                                        <motion.div
                                            key={index}
                                            className={`p-2 sm:p-3 lg:p-3 xl:p-3 2xl:p-3 rounded-lg transition-all duration-500 cursor-pointer select-none ${currentStep === index
                                                ? 'bg-blue-50 dark:bg-blue-900/20'
                                                : 'hover:bg-slate-100 dark:hover:bg-slate-700/50'
                                                }`}
                                            onClick={() => goToStep(index)}
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                        >
                                            <div className="flex items-start space-x-2 sm:space-x-3 lg:space-x-3 xl:space-x-3 2xl:space-x-3">
                                                <div className={`w-8 h-8 sm:w-10 sm:h-10 lg:w-10 lg:h-10 xl:w-10 xl:h-10 2xl:w-10 2xl:h-10 rounded-lg flex items-center justify-center transition-all duration-500 ${currentStep === index
                                                    ? 'bg-gradient-to-r from-blue-500 to-purple-500'
                                                    : 'bg-slate-100 dark:bg-slate-700'
                                                    }`}>
                                                    <step.icon className={`w-4 h-4 sm:w-5 sm:h-5 lg:w-5 lg:h-5 xl:w-5 xl:h-5 2xl:w-5 2xl:h-5 transition-colors duration-500 ${currentStep === index ? 'text-white' : 'text-slate-600 dark:text-slate-400'
                                                        }`} />
                                                </div>
                                                <div className="flex-1">
                                                    <h3 className={`text-sm sm:text-base lg:text-lg xl:text-lg 2xl:text-lg font-bold transition-colors duration-500 ${currentStep === index
                                                        ? 'text-blue-800 dark:text-blue-200'
                                                        : 'text-slate-800 dark:text-slate-200'
                                                        }`}>
                                                        {step.title}
                                                    </h3>
                                                    <p className={`text-xs sm:text-sm lg:text-sm xl:text-sm 2xl:text-sm transition-colors duration-500 leading-relaxed ${currentStep === index
                                                        ? 'text-blue-600 dark:text-blue-300'
                                                        : 'text-slate-600 dark:text-slate-400'
                                                        }`}>
                                                        {step.description}
                                                    </p>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        </motion.div>
                    </div>
                    

                    {/* Right: Fixed Title, Subtitle and Steps */}
                    <div className="w-full lg:w-3/5 pr-0 lg:pr-8 flex justify-center">
                        <motion.div
                            initial={{ opacity: 0, y: 50 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.8, delay: 0.2 }}
                            className="relative z-40 w-full max-w-4xl"
                        >
                            {/* Clean Content Container */}
                            <div className="relative w-full px-2 sm:px-4 lg:px-8 xl:px-12">
                                <motion.div
                                    key={currentStep}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -20 }}
                                    transition={{ duration: 0.6 }}
                                    className="w-full p-2 sm:p-4 lg:p-8"
                                >
                                    {currentStepData.content(currentStepData.title, currentStepData.description)}
                                </motion.div>
                            </div>
                        </motion.div>
                    </div>
                    
                </ParallaxLayer>

            </Parallax>
        </div>
    );
}
