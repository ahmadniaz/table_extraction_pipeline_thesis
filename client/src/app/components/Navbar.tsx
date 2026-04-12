'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Moon, Sun, FlaskConical } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { cn } from '@/lib/utils';

const NAV_LINKS = [
  { href: '/corpus', label: 'Corpus' },
  { href: '/results', label: 'Results' },
];

export default function Navbar() {
  const pathname = usePathname();
  const { actualTheme, setTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-6">
        {/* Brand */}
        <Link href="/corpus" className="flex items-center gap-2 shrink-0">
          <FlaskConical className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <span className="font-semibold text-slate-800 dark:text-slate-100 text-sm whitespace-nowrap">
            PDF Table Extraction Evaluator
          </span>
        </Link>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          {NAV_LINKS.map(({ href, label }) => {
            const active = pathname?.startsWith(href) ?? false;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                  active
                    ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100'
                )}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Theme toggle */}
        <button
          onClick={() => setTheme(actualTheme === 'dark' ? 'light' : 'dark')}
          className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          aria-label="Toggle theme"
        >
          {actualTheme === 'dark' ? (
            <Sun className="w-4 h-4 text-slate-500 dark:text-slate-400" />
          ) : (
            <Moon className="w-4 h-4 text-slate-500" />
          )}
        </button>
      </div>
    </header>
  );
}
