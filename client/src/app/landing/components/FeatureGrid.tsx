'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, 
  BarChart3, 
  DollarSign, 
  Shield, 
  Users
} from 'lucide-react';

const features = [
  {
    icon: FileText,
    title: "AI-Powered Document Processing",
    description: "Automatically extract and process commission statements from multiple carriers",
    color: "from-blue-500 to-cyan-500",
    bgColor: "from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20"
  },
  {
    icon: BarChart3,
    title: "Analytics & Insights",
    description: "Get detailed analytics on your commission performance with real-time dashboards",
    color: "from-purple-500 to-pink-500",
    bgColor: "from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20"
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description: "Bank-level security with OTP authentication and data encryption",
    color: "from-orange-500 to-red-500",
    bgColor: "from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20"
  },
];


export default function FeatureGrid() {
  return (
    <div className="w-full max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-12 sm:py-16 lg:py-20">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-2xl sm:text-3xl lg:text-4xl xl:text-5xl font-bold text-slate-800 dark:text-slate-200 mb-3 sm:mb-4">
            Everything you need to manage commissions
          </h2>
          <p className="text-base sm:text-lg lg:text-xl xl:text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto">
            Our comprehensive platform provides all the tools you need to streamline your commission tracking and gain valuable insights.
          </p>
        </motion.div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8 mb-12 sm:mb-16">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
                className="group"
              >
                <div className={`p-4 sm:p-6 lg:p-8 rounded-xl sm:rounded-2xl bg-gradient-to-br ${feature.bgColor} transition-all duration-300 h-full`}>
                  <div className={`w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-r ${feature.color} rounded-lg sm:rounded-xl flex items-center justify-center mb-4 sm:mb-6 group-hover:scale-110 transition-transform duration-300`}>
                    <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                  </div>
                  <h3 className="text-lg sm:text-xl lg:text-xl xl:text-2xl font-bold text-slate-800 dark:text-slate-200 mb-3 sm:mb-4">
                    {feature.title}
                  </h3>
                  <p className="text-sm sm:text-base lg:text-base xl:text-lg text-slate-600 dark:text-slate-400 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>

      </div>
  );
}
