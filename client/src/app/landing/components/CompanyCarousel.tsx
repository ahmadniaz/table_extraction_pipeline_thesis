'use client';

import React from 'react';
import { motion } from 'framer-motion';

const companies = [
  { index: 1, name: '90 Degree', logo: '90D' },
  { index: 2, name: 'Aetna', logo: 'AET' },
  { index: 3, name: 'Alera Highmark Group', logo: 'AHG' },
  { index: 4, name: 'Allstate Health - Allied', logo: 'AHA' },
  { index: 5, name: 'Amerihealth/BenefitMall', logo: 'AMB' },
  { index: 6, name: 'Angle', logo: 'ANG' },
  { index: 7, name: 'Anthem Blue Cross', logo: 'ABC' },
  { index: 8, name: 'Anthem KY - Agent Link', logo: 'AKY' },
  { index: 9, name: 'Apex', logo: 'APX' },
  { index: 10, name: 'Assured Benefits Administrators', logo: 'ABA' },
  { index: 11, name: 'BCBS', logo: 'BCB' },
  { index: 12, name: 'Beni Solutions', logo: 'BEN' },
  { index: 13, name: 'Black Hawk', logo: 'BHK' },
  { index: 14, name: 'Breckpoint', logo: 'BRK' },
  { index: 15, name: 'California Choice', logo: 'CAL' },
  { index: 16, name: 'Elan', logo: 'ELN' },
  { index: 17, name: 'EMI Health', logo: 'EMI' },
  { index: 18, name: 'Gravie', logo: 'GRV' },
  { index: 19, name: 'HealthNet', logo: 'HNT' },
  { index: 20, name: 'IHP', logo: 'IHP' },
  { index: 21, name: 'Aflac', logo: 'AFL' },
  { index: 22, name: 'Allstate VB', logo: 'AVB' },
  { index: 23, name: 'Ameritas', logo: 'AMT' },
  { index: 24, name: 'BEAM', logo: 'BEM' },
  { index: 25, name: 'Colonial', logo: 'COL' },
  { index: 26, name: 'Delta', logo: 'DEL' },
  { index: 27, name: 'Guardian', logo: 'GUA' },
  { index: 28, name: 'Humana', logo: 'HUM' },
  { index: 29, name: 'MetLife', logo: 'MET' },
  { index: 30, name: 'Nippon Life', logo: 'NIP' },
  { index: 31, name: 'Principal', logo: 'PRI' },
  { index: 32, name: 'Sunlife', logo: 'SUN' },
  { index: 33, name: 'Unum', logo: 'UNM' },
  { index: 34, name: 'VSP', logo: 'VSP' },
  { index: 35, name: 'Independent Health', logo: 'IND' },
  { index: 36, name: 'Kaiser', logo: 'KAI' },
  { index: 37, name: 'MEC', logo: 'MEC' },
  { index: 38, name: 'MediExcel', logo: 'MED' },
  { index: 39, name: 'Memorial Herman', logo: 'MEM' },
  { index: 40, name: 'MVP', logo: 'MVP' },
  { index: 41, name: 'Optimyl', logo: 'OPT' },
  { index: 42, name: 'Paramount', logo: 'PAR' },
  { index: 43, name: 'Physicians Health Plan (PHP)', logo: 'PHP' },
  { index: 44, name: 'Qual Choice', logo: 'QCH' },
  { index: 45, name: 'Redirect Health', logo: 'RED' },
  { index: 46, name: 'Regence 2025 Commission Schedule', logo: 'REG' },
  { index: 47, name: 'Take Command', logo: 'TCM' },
  { index: 48, name: 'The Big Plan', logo: 'TBP' },
  { index: 49, name: 'UHC', logo: 'UHC' },
  { index: 50, name: 'UHC Oxford', logo: 'UOX' },
  { index: 51, name: 'UPMC', logo: 'UPM' },
  { index: 52, name: 'Zizzl Health - ICHRA', logo: 'ZIZ' }
];

export default function CompanyCarousel() {
  return (
    <div className="w-full max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8 sm:py-12 lg:py-16">

        {/* Carousel Container */}
        <div className="relative overflow-hidden">
          <div 
            className="flex gap-1 items-center animate-scroll"
            style={{
              width: 'max-content',
              animation: 'scroll 300s linear infinite'
            }}
          >
            {/* First set of companies */}
            {companies.map((company, index) => (
              <div
                key={`first-${company.index}-${index}`}
                className="flex-shrink-0 flex items-center justify-center px-4 sm:px-6 lg:px-8 hover:scale-105 transition-transform duration-200"
              >
                <span className="text-lg sm:text-xl lg:text-2xl 2xl:text-2xl font-light text-slate-600 dark:text-slate-400 tracking-wide whitespace-nowrap">
                  {company.name}
                </span>
              </div>
            ))}
            
            {/* Duplicate set for seamless loop */}
            {companies.map((company, index) => (
              <div
                key={`second-${company.index}-${index}`}
                className="flex-shrink-0 flex items-center justify-center px-4 sm:px-6 lg:px-8 hover:scale-105 transition-transform duration-200"
              >
                <span className="text-lg sm:text-xl lg:text-2xl 2xl:text-2xl font-light text-slate-600 dark:text-slate-400 tracking-wide whitespace-nowrap">
                  {company.name}
                </span>
              </div>
            ))}
          </div>
        </div>
        
        <style jsx>{`
          @keyframes scroll {
            0% {
              transform: translateX(0);
            }
            100% {
              transform: translateX(-100%);
            }
          }
        `}</style>
      </div>
  );
}
