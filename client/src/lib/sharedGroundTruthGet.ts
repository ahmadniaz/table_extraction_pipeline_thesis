import axios, { type AxiosResponse } from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

/** Deduplicates in-flight GET /api/ground-truth/{docId} (e.g. React StrictMode double mount). */
const inflight = new Map<string, Promise<AxiosResponse<unknown>>>();

export function sharedGetGroundTruth(docId: string): Promise<AxiosResponse<unknown>> {
  let p = inflight.get(docId);
  if (!p) {
    p = axios.get(`${API}/api/ground-truth/${docId}`).finally(() => {
      inflight.delete(docId);
    });
    inflight.set(docId, p);
  }
  return p;
}
