import { useState, useEffect, useRef } from 'react';

interface UseSectionVisibilityOptions {
  threshold?: number; // 0-1, default 1.0 (100%)
  rootMargin?: string; // default '0px'
  debug?: boolean; // default false
}

interface SectionVisibilityState {
  isFullyVisible: boolean;
  scrollProgress: number;
  isIntersecting: boolean;
  intersectionRatio: number;
}

export const useSectionVisibility = (options: UseSectionVisibilityOptions = {}) => {
  const {
    threshold = 1.0,
    rootMargin = '0px',
    debug = false
  } = options;

  const [state, setState] = useState<SectionVisibilityState>({
    isFullyVisible: false,
    scrollProgress: 0,
    isIntersecting: false,
    intersectionRatio: 0
  });

  const sectionRef = useRef<HTMLDivElement>(null);

  // Método 1: Intersection Observer (más preciso)
  useEffect(() => {
    const el = sectionRef.current;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const isIntersecting = entry.isIntersecting;
          const intersectionRatio = entry.intersectionRatio;
          const isFullyVisible = intersectionRatio >= threshold;

          setState(prev => ({
            ...prev,
            isFullyVisible,
            isIntersecting,
            intersectionRatio
          }));

          if (debug) {
            console.log('🎯 Section Visibility:', {
              isIntersecting,
              intersectionRatio: Math.round(intersectionRatio * 100) + '%',
              isFullyVisible,
              threshold: Math.round(threshold * 100) + '%'
            });
          }
        });
      },
      {
        threshold,
        rootMargin
      }
    );

    if (el) {
      observer.observe(el);
    }

    return () => {
      if (el) {
        observer.unobserve(el);
      }
    };
  }, [threshold, rootMargin, debug]);

  // Método 2: Scroll position detection (más granular)
  useEffect(() => {
    const handleScroll = () => {
      if (!sectionRef.current) return;
      
      const rect = sectionRef.current.getBoundingClientRect();
      const windowHeight = window.innerHeight;
      
      // Calcular qué porcentaje de la sección está visible
      const visibleHeight = Math.min(rect.bottom, windowHeight) - Math.max(rect.top, 0);
      const sectionHeight = rect.height;
      
      // Calcular el centro de la sección y el centro de la ventana
      const sectionCenter = rect.top + (sectionHeight / 2);
      const windowCenter = windowHeight / 2;
      const distanceFromCenter = Math.abs(sectionCenter - windowCenter);
      
      // Calcular el scroll progress basado en qué tan centrada está la sección
      // Solo considerar cuando la sección está al menos 80% visible
      let scrollProgress = 0;
      if (visibleHeight >= sectionHeight * 0.8) {
        // El scroll progress se basa en qué tan centrada está la sección
        // 100% = perfectamente centrada, 0% = muy lejos del centro
        const maxDistance = windowHeight * 0.4; // Distancia máxima para considerar
        const centeringRatio = Math.max(0, 1 - (distanceFromCenter / maxDistance));
        
        // Combinar visibilidad y centrado
        const visibilityRatio = visibleHeight / sectionHeight;
        scrollProgress = Math.max(0, Math.min(100, (centeringRatio * visibilityRatio) * 100));
      }
      
      setState(prev => ({
        ...prev,
        scrollProgress
      }));

      if (debug && scrollProgress >= 50) {
        const maxDistance = windowHeight * 0.4;
        const centeringRatio = Math.max(0, 1 - (distanceFromCenter / maxDistance));
        const visibilityRatio = visibleHeight / sectionHeight;
        
        console.log('🎯 Section scroll progress:', Math.round(scrollProgress) + '%', {
          visibleHeight: Math.round(visibleHeight),
          sectionHeight: Math.round(sectionHeight),
          sectionCenter: Math.round(sectionCenter),
          windowCenter: Math.round(windowCenter),
          distanceFromCenter: Math.round(distanceFromCenter),
          centeringRatio: Math.round(centeringRatio * 100) + '%',
          visibilityRatio: Math.round(visibilityRatio * 100) + '%'
        });
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [debug]);

  return {
    sectionRef,
    ...state
  };
};
