/**
 * Performance Optimization Utilities
 */

/**
 * Batch multiple state updates into a single re-render
 */
export function batchUpdates<T>(updates: (() => void)[]): void {
  // React 18 automatic batching handles this, but we can wrap for explicit control
  updates.forEach(update => update());
}

/**
 * Throttle function execution
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  return function(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Memoize function results
 */
export function memoize<T extends (...args: any[]) => any>(fn: T): T {
  const cache = new Map<string, ReturnType<T>>();
  return ((...args: Parameters<T>) => {
    const key = JSON.stringify(args);
    if (cache.has(key)) {
      return cache.get(key);
    }
    const result = fn(...args);
    cache.set(key, result);
    return result;
  }) as T;
}

/**
 * Request idle callback wrapper with fallback
 */
export function requestIdleCallback(callback: () => void, timeout = 1000): number {
  if (typeof window === 'undefined') {
    return 0;
  }
  
  if ('requestIdleCallback' in window) {
    return window.requestIdleCallback(callback, { timeout });
  }
  
  return (window as Window).setTimeout(callback, 1) as any;
}

/**
 * Cancel idle callback with fallback
 */
export function cancelIdleCallback(id: number): void {
  if (typeof window !== 'undefined' && 'cancelIdleCallback' in window) {
    window.cancelIdleCallback(id);
  } else {
    clearTimeout(id);
  }
}

/**
 * Measure render performance
 */
export function measurePerformance(componentName: string, callback: () => void): void {
  if (process.env.NODE_ENV === 'development') {
    const start = performance.now();
    callback();
    const end = performance.now();
    console.log(`[Performance] ${componentName}: ${(end - start).toFixed(2)}ms`);
  } else {
    callback();
  }
}

