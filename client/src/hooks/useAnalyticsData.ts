import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { buildDocumentToolRows, filterDocumentToolRows } from '@/lib/analytics/buildDataset';
import {
  type AnalyticsFilterState,
  type DocumentMeta,
  type DocumentToolAggregate,
  type ExtractionTableRow,
  defaultAnalyticsFilters,
} from '@/lib/analytics/types';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type ApiDataset = {
  documents: DocumentMeta[];
  extraction_table_rows: ExtractionTableRow[];
  all_tool_ids: string[];
};

export function useAnalyticsData() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [tableRows, setTableRows] = useState<ExtractionTableRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draftFilters, setDraftFilters] = useState<AnalyticsFilterState>(defaultAnalyticsFilters);
  const [appliedFilters, setAppliedFilters] = useState<AnalyticsFilterState>(defaultAnalyticsFilters);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await axios.get<ApiDataset>(`${API}/api/analytics/dataset`);
      setDocuments(data.documents);
      setTableRows(data.extraction_table_rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load analytics dataset');
      setDocuments([]);
      setTableRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const allDocToolRows = useMemo(
    () => buildDocumentToolRows(documents, tableRows),
    [documents, tableRows]
  );

  const filteredDocToolRows = useMemo(
    () => filterDocumentToolRows(allDocToolRows, appliedFilters),
    [allDocToolRows, appliedFilters]
  );

  const applyFilters = useCallback(() => {
    setAppliedFilters({ ...draftFilters });
  }, [draftFilters]);

  const resetFilters = useCallback(() => {
    setDraftFilters({ ...defaultAnalyticsFilters });
    setAppliedFilters({ ...defaultAnalyticsFilters });
  }, []);

  return {
    documents,
    tableRows,
    allDocToolRows,
    filteredDocToolRows,
    loading,
    error,
    reload: load,
    draftFilters,
    setDraftFilters,
    appliedFilters,
    applyFilters,
    resetFilters,
  };
}
