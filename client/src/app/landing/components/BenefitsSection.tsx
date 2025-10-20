'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Clock } from 'lucide-react';

const benefits = [
  "Save 15+ Hours Weekly — Eliminate manual reconciliation forever",
  "Reduce Errors by 95% — AI ensures accuracy across all carriers",
  "Boost Team Productivity — Deliver instant, data-driven insights to clients",
  "Scale Without Limits — Onboard new carriers in minutes, not weeks"
];

export default function BenefitsSection() {
  return (
    <section className="py-12 sm:py-16 lg:py-20 bg-slate-50 dark:bg-slate-900">
      <div className="w-full max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="rounded-xl sm:rounded-2xl p-4 sm:p-6 lg:p-8"
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8 items-center">
            <div>
              <h3 className="text-xl sm:text-2xl lg:text-3xl xl:text-4xl font-bold text-slate-800 dark:text-slate-200 mb-3 sm:mb-4">
                Why choose Commission Tracker?
              </h3>
              <p className="text-base sm:text-lg lg:text-xl xl:text-xl text-slate-600 dark:text-slate-400 mb-4 sm:mb-6">
                Join thousands of financial professionals who have transformed their commission management with our platform.
              </p>
              <div className="space-y-3">
                {benefits.map((benefit, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4, delay: index * 0.1 }}
                    viewport={{ once: true }}
                    className="flex items-center gap-3"
                  >
                    <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6 text-green-500 flex-shrink-0" />
                    <span className="text-sm sm:text-base lg:text-lg xl:text-lg text-slate-700 dark:text-slate-400 font-medium">{benefit}</span>
                  </motion.div>
                ))}
              </div>
            </div>
            <div className="relative">
              <div className="bg-white dark:bg-slate-800 rounded-lg sm:rounded-xl p-4 sm:p-6">
                <div className="flex items-center gap-2 sm:gap-3 mb-3 sm:mb-4">
                  <div className="w-6 h-6 sm:w-8 sm:h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                    <Clock className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
                  </div>
                  <span className="text-sm sm:text-base lg:text-lg xl:text-lg font-semibold text-slate-800 dark:text-slate-200">Time Saved</span>
                </div>
                <div className="text-2xl sm:text-3xl lg:text-4xl xl:text-5xl font-bold text-slate-800 dark:text-slate-200 mb-1 sm:mb-2">15+ hours</div>
                <div className="text-slate-600 dark:text-slate-400 text-xs sm:text-sm lg:text-base xl:text-base">per week on average</div>
                <div className="mt-3 sm:mt-4 bg-slate-100 dark:bg-slate-700 rounded-lg p-2 sm:p-3">
                  <div className="text-xs sm:text-sm lg:text-base xl:text-base text-slate-600 dark:text-slate-400 mb-1">Efficiency Gain</div>
                  <div className="w-full bg-slate-200 dark:bg-slate-600 rounded-full h-1.5 sm:h-2">
                    <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-1.5 sm:h-2 rounded-full w-4/5"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
