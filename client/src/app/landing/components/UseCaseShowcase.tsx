'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { 
  Building2, 
  Users, 
  TrendingUp, 
  Shield,
  ArrowRight,
  CheckCircle,
  Star
} from 'lucide-react';

const useCases = [
  {
    title: "Insurance Agencies",
    description: "Streamline commission tracking for insurance agents and agencies",
    icon: Shield,
    color: "from-blue-500 to-cyan-500",
    bgColor: "from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20",
    features: [
      "Multi-carrier support",
      "Automated statement processing",
      "Commission reconciliation",
      "Performance analytics"
    ],
    stats: { value: "95%", label: "Time Saved" }
  },
  {
    title: "Financial Advisors",
    description: "Manage investment commissions and track client performance",
    icon: TrendingUp,
    color: "from-green-500 to-emerald-500",
    bgColor: "from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20",
    features: [
      "Investment tracking",
      "Client portfolio analysis",
      "Commission forecasting",
      "Regulatory compliance"
    ],
    stats: { value: "10x", label: "Faster Processing" }
  },
  {
    title: "Brokerage Firms",
    description: "Enterprise-level commission management for large organizations",
    icon: Building2,
    color: "from-purple-500 to-pink-500",
    bgColor: "from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20",
    features: [
      "Team collaboration",
      "Role-based access",
      "Advanced reporting",
      "API integrations"
    ],
    stats: { value: "50+", label: "Users Supported" }
  }
];

const testimonials = [
  {
    name: "Sarah Johnson",
    role: "CEO",
    company: "Premier Insurance Group",
    content: "Commission Tracker has revolutionized how we manage our commission data. The automation saves us hours every week.",
    rating: 5,
    avatar: "SJ"
  },
  {
    name: "Michael Chen",
    role: "Sales Manager",
    company: "Metro Financial Services",
    content: "The analytics dashboard gives us insights we never had before. Our team productivity has increased by 40%.",
    rating: 5,
    avatar: "MC"
  },
  {
    name: "Emily Rodriguez",
    role: "Financial Advisor",
    company: "Capital Wealth Management",
    content: "Finally, a solution that handles all our carrier statements in one place. Highly recommended!",
    rating: 5,
    avatar: "ER"
  }
];

export default function UseCaseShowcase() {
  return (
    <section className="py-12 sm:py-16 lg:py-20 bg-white dark:bg-slate-800">
      <div className="w-full max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-2xl sm:text-3xl lg:text-4xl 2xl:text-4xl font-bold text-slate-800 dark:text-slate-200 mb-3 sm:mb-4">
            Built for every type of financial professional
          </h2>
          <p className="text-base sm:text-lg lg:text-xl 2xl:text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto">
            Whether you&apos;re an individual agent or a large brokerage firm, Commission Tracker adapts to your needs.
          </p>
        </motion.div>

        {/* Testimonials */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="mb-16"
        >
          <div className="text-center mb-8 sm:mb-12">
            <h3 className="text-xl sm:text-2xl font-bold text-slate-800 dark:text-slate-200 mb-3 sm:mb-4">
              What our customers say
            </h3>
            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400">
              Join hundreds of satisfied customers who have transformed their commission tracking.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
                className="bg-slate-50 dark:bg-slate-700 p-4 sm:p-6 rounded-xl sm:rounded-2xl border border-slate-200 dark:border-slate-600"
              >
                <div className="flex items-center mb-3 sm:mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="w-3 h-3 sm:w-4 sm:h-4 text-yellow-400 fill-current" />
                  ))}
                </div>
                <blockquote className="text-sm sm:text-base text-slate-600 dark:text-slate-400 mb-3 sm:mb-4 italic">
                  &quot;{testimonial.content}&quot;
                </blockquote>
                <div className="flex items-center gap-2 sm:gap-3">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-semibold text-sm sm:text-base">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className="text-sm sm:text-base font-semibold text-slate-800 dark:text-slate-200">
                      {testimonial.name}
                    </div>
                    <div className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                      {testimonial.role} at {testimonial.company}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
