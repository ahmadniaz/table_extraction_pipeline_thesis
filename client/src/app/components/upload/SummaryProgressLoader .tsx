/**
 * Premium Progress Loader Component
 * 
 * Elegant step-by-step loader with circular progress, step indicators,
 * and estimated time remaining.
 */

"use client";

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export interface UploadStep {
  id: string;
  order: number;
  title: string;
  description: string;
  estimatedDuration: number;
}

export const UPLOAD_STEPS: UploadStep[] = [
  {
    id: 'upload',
    order: 1,
    title: 'Uploading File',
    description: 'Securing your document...',
    estimatedDuration: 2000
  },
  {
    id: 'extraction',
    order: 2,
    title: 'Extracting Metadata',
    description: 'AI is analyzing document structure...',
    estimatedDuration: 5000
  },
  {
    id: 'table_extraction',
    order: 3,
    title: 'Processing Table Data',
    description: 'Extracting commission data...',
    estimatedDuration: 7000
  },
  {
    id: 'plan_detection',
    order: 4,
    title: 'Detecting Plan Type',
    description: 'Identifying insurance plan category...',
    estimatedDuration: 2000
  },
  {
    id: 'finalizing',
    order: 5,
    title: 'Finalizing',
    description: 'Preparing your data for review...',
    estimatedDuration: 1000
  },
];

interface PremiumProgressLoaderProps {
  currentStep: number;
  steps?: UploadStep[];
  progress: number;
  estimatedTime?: string;
  isVisible?: boolean;
  pdfUrl?: string | null;
  onContinue?: () => void; // 🚫 PAUSE POINT: Manual continue button - remove when reverting to automatic
  summaryContent?: string; // Summary content
  metadataContent?: string; // Metadata content
}

export default function PremiumProgressLoader({
  currentStep,
  steps = UPLOAD_STEPS,
  progress,
  estimatedTime,
  isVisible = true,
  pdfUrl,
  onContinue,
  summaryContent,
  metadataContent
}: PremiumProgressLoaderProps) {
  const [animatedProgress, setAnimatedProgress] = useState(0);
  const [countdown, setCountdown] = useState(10);
  const [isCountdownActive, setIsCountdownActive] = useState(false);

  // Check if step 5 (Finalizing) is completed for continue button
  const isStep5Completed = currentStep >= 5 || progress >= 100;
  const isCompleted = progress >= 100;

  // Smooth progress animation
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedProgress(progress);
    }, 100);
    return () => clearTimeout(timer);
  }, [progress]);

  // Countdown logic
  useEffect(() => {
    if (isStep5Completed && !isCountdownActive) {
      setIsCountdownActive(true);
      setCountdown(10);
    }
  }, [isStep5Completed, isCountdownActive]);

  useEffect(() => {
    if (isCountdownActive && countdown > 0) {
      const timer = setTimeout(() => {
        setCountdown(countdown - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (isCountdownActive && countdown === 0) {
      // Auto-continue when countdown reaches 0
      if (onContinue) {
        onContinue();
      }
    }
  }, [isCountdownActive, countdown, onContinue]);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 animate-fadeIn p-4 bg-black/50 backdrop-blur-sm">
      <div className="p-4 w-full sm:w-4/5 h-full mx-auto animate-slideIn overflow-visible bg-white dark:bg-transparent rounded-2xl shadow-2xl">
        <div className="grid grid-cols-5 gap-6 h-full">
          {/* Left Column - Progress Steps (1/5) */}
          <div className="flex flex-col col-span-1">
        
        {/* Main Progress Circle */}
        <div className="flex flex-col items-center mb-8 p-4">
          <div className="relative w-24 h-24 mb-4 overflow-visible">
            <CircularProgress value={animatedProgress} />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-semibold text-gray-800 dark:text-white">
                {Math.round(animatedProgress)}%
              </span>
            </div>
          </div>
          
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white text-center">
            Processing Your File
          </h2>
        </div>

        {/* Step Indicators */}
        <div className="space-y-3">
          {steps.map((step, index) => (
            <StepIndicator
              key={step.id}
              step={step}
              isActive={index === currentStep && !(index === 4 && progress >= 100)}
              isCompleted={index < currentStep || (index === 4 && progress >= 100)}
              isNext={index === currentStep + 1}
            />
          ))}
        </div>

        {/* Estimated Time */}
        {estimatedTime && !isCompleted && (
          <div className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
            <p>Estimated time: {estimatedTime} remaining</p>
          </div>
        )}

        {/* Continue Button - Always visible, enabled when step 5 is completed */}
        {onContinue && (
          <div className="mt-8 flex justify-center">
            <button
              onClick={isStep5Completed ? onContinue : undefined}
              disabled={!isStep5Completed}
              className={`px-8 py-3 rounded-xl font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                isStep5Completed
                  ? 'bg-gradient-to-r from-green-500 to-blue-600 text-white hover:shadow-lg hover:scale-105 focus:ring-blue-500'
                  : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
              }`}
            >
              <div className="flex items-center gap-2">
                {isStep5Completed ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                {isStep5Completed 
                  ? (isCountdownActive && countdown > 0 ? `Continuing in ${countdown}s` : 'Continue')
                  : 'Processing...'
                }
              </div>
            </button>
          </div>
        )}
          </div>
          
          {/* Center Column - PDF Viewer (3/5) */}
          <div className="flex flex-col col-span-3">
            {pdfUrl ? (
              <div className="flex-1 overflow-hidden rounded-lg shadow-lg border border-gray-200 dark:border-gray-600">
                <iframe
                  src={`${pdfUrl}#toolbar=1&navpanes=0&scrollbar=1&view=FitH&statusbar=0&menubar=0&header=0&footer=0&zoom=100&pagemode=none`}
                  className="w-full h-full border-0 rounded-lg scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600 scrollbar-track-gray-100 dark:scrollbar-track-gray-800"
                  title="PDF Preview"
                  style={{ 
                    minHeight: '500px',
                    filter: 'brightness(1.1) contrast(1.05)',
                    backgroundColor: '#f8fafc'
                  }}
                />
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800 rounded-lg border border-gray-200 dark:border-gray-600">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-gray-500 dark:text-gray-400 font-medium">No document preview available</p>
                </div>
              </div>
            )}
          </div>
          
          {/* Right Column - Content (1/5) */}
          <div className="flex flex-col col-span-1">
            <div className="flex-1 overflow-auto rounded-lg p-2 bg-transparent max-h-[90vh]">
              <div className="prose prose-sm dark:prose-invert max-w-none overflow-x-auto overflow-y-auto">
                
                {/* Summary Section - Always visible */}
                <div className="mb-6">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-0.5 bg-blue-500"></div>
                    <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide">
                      Summary
                    </span>
                    <div className="flex-1 h-0.5 bg-gradient-to-r from-blue-500 to-transparent"></div>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 italic mb-3">
                    File summary and document overview
                  </p>
                  
                  {/* Content or Thinking Animation */}
                  {summaryContent ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown>
                        {summaryContent}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="text-left">
                      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <span>thinking</span>
                        <div className="flex space-x-1">
                          <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                          <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Metadata Section - Only show if content exists */}
                {metadataContent && (
                  <div className="mt-6">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-8 h-0.5 bg-blue-500"></div>
                      <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide">
                        File Metadata
                      </span>
                      <div className="flex-1 h-0.5 bg-gradient-to-r from-blue-500 to-transparent"></div>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 italic mb-3">
                      Information extracted directly from the document
                    </p>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown>
                        {metadataContent}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}

              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Circular Progress Component
function CircularProgress({ value }: { value: number }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  return (
    <svg className="w-full h-full transform -rotate-90 overflow-visible" viewBox="0 0 100 100">
      {/* Background circle */}
      <circle
        cx="48"
        cy="48"
        r={radius}
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
        className="text-gray-200 dark:text-gray-700"
      />
      {/* Progress circle */}
      <circle
        cx="48"
        cy="48"
        r={radius}
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
        strokeDasharray={circumference}
        strokeDashoffset={strokeDashoffset}
        className="text-blue-600 dark:text-blue-400 transition-all duration-500 ease-out"
        strokeLinecap="round"
      />
    </svg>
  );
}

// Step Indicator Component
interface StepIndicatorProps {
  step: UploadStep;
  isActive: boolean;
  isCompleted: boolean;
  isNext: boolean;
}

function StepIndicator({ step, isActive, isCompleted, isNext }: StepIndicatorProps) {
  return (
    <div
      className={`
        flex items-center p-3 rounded-lg transition-all duration-500
        ${isActive ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-600' : ''}
        ${isCompleted ? 'bg-green-50 dark:bg-green-900/20' : ''}
      `}
    >
      {/* Icon */}
      <div
        className={`
          w-8 h-8 rounded-full flex items-center justify-center mr-3 transition-all duration-300 flex-shrink-0
          ${
            isCompleted
              ? 'bg-green-600 text-white'
              : isActive
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
          }
        `}
      >
        {isCompleted ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : isActive ? (
          <div className="relative">
            <div className="w-3 h-3 bg-white rounded-full"></div>
            <div className="absolute inset-0 w-3 h-3 bg-white rounded-full animate-ping"></div>
          </div>
        ) : (
          <span className="text-sm font-medium">{step.order}</span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={`
            font-medium transition-colors duration-200 truncate
            ${
              isActive
                ? 'text-blue-800 dark:text-blue-300'
                : isCompleted
                ? 'text-green-800 dark:text-green-300'
                : 'text-gray-600 dark:text-gray-400'
            }
          `}
        >
          {step.title}
        </p>
        {isActive && (
          <p className="text-sm text-blue-600 dark:text-blue-400 mt-1 animate-fadeIn truncate">
            {step.description}
          </p>
        )}
      </div>

      {/* Loading Spinner for Active Step */}
      {isActive && !isCompleted && (
        <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin flex-shrink-0 ml-2"></div>
      )}
    </div>
  );
}

