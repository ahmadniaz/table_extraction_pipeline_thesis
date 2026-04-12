import axios, { type AxiosResponse } from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

/**
 * Deduplicates in-flight GET /api/extractions/{docId}/{toolName} when no AbortSignal is passed.
 * Covers React Strict Mode, refreshTool + editor modal racing the same URL, etc.
 * Callers that need cancellation should pass `signal` (bypasses dedupe).
 */
const inflight = new Map<string, Promise<AxiosResponse<unknown>>>();

function cacheKey(docId: string, toolName: string) {
  return `${docId}\0${toolName}`;
}

export function sharedGetExtractionsForTool<T = unknown>(
  docId: string,
  toolName: string,
  config?: { signal?: AbortSignal }
): Promise<AxiosResponse<T>> {
  if (config?.signal) {
    return axios.get<T>(`${API}/api/extractions/${docId}/${toolName}`, {
      signal: config.signal,
    });
  }
  const k = cacheKey(docId, toolName);
  let p = inflight.get(k) as Promise<AxiosResponse<T>> | undefined;
  if (!p) {
    p = axios.get<T>(`${API}/api/extractions/${docId}/${toolName}`).finally(() => {
      inflight.delete(k);
    });
    inflight.set(k, p as Promise<AxiosResponse<unknown>>);
  }
  return p;
}
