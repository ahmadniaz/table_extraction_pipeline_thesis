'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Mail, CheckCircle } from 'lucide-react';

interface RegistrationFormProps {
  onSubmit: (email: string) => void;
}

export default function RegistrationForm({ onSubmit }: RegistrationFormProps) {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setIsLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setIsSubmitted(true);
    setIsLoading(false);
    
    // Call the parent onSubmit after a brief delay
    setTimeout(() => {
      onSubmit(email);
    }, 1500);
  };

  if (isSubmitted) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center py-8"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4"
        >
          <CheckCircle className="w-8 h-8 text-white" />
        </motion.div>
        <h3 className="text-xl font-bold text-slate-800 dark:text-slate-200 mb-2">
          Welcome aboard! 🎉
        </h3>
        <p className="text-slate-600 dark:text-slate-400 mb-4">
          We&apos;ve sent you a confirmation email with next steps.
        </p>
        <div className="text-sm text-slate-500 dark:text-slate-400">
          Redirecting to registration...
        </div>
      </motion.div>
    );
  }

  return (
    <motion.form
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Mail className="h-5 w-5 text-slate-500" />
          </div>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email address"
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-white/20 bg-white/95 backdrop-blur-sm text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-white/30 transition-all duration-200 shadow-lg"
            required
          />
        </div>
        <motion.button
          type="submit"
          disabled={isLoading || !email.trim()}
          whileHover={{ scale: isLoading ? 1 : 1.05 }}
          whileTap={{ scale: isLoading ? 1 : 0.95 }}
          className={`px-6 py-3 rounded-xl font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
            isLoading || !email.trim()
              ? 'bg-white/30 text-white/60 cursor-not-allowed border border-white/20'
              : 'bg-white text-blue-600 hover:bg-blue-50 shadow-lg hover:shadow-xl cursor-pointer border border-white/30'
          }`}
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              Processing...
            </>
          ) : (
            <>
              Get Started
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </motion.button>
      </div>
      
      <div className="text-center">
        <p className="text-sm text-white/80">
          No credit card required • 14-day free trial
        </p>
      </div>
    </motion.form>
  );
}
