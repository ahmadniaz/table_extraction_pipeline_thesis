'use client';

import { useState, useEffect } from 'react';
import { useTheme } from '@/context/ThemeContext';

/**
 * Custom hook to handle theme hydration issues
 * Prevents hydration mismatches by ensuring theme-dependent content
 * only renders after the component has mounted on the client
 */
export function useThemeHydration() {
  const { actualTheme, theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return {
    mounted,
    actualTheme,
    isDark: mounted && actualTheme === 'dark',
    isLight: mounted && actualTheme === 'light',
    isSystem: mounted && theme === 'system'
  };
}
