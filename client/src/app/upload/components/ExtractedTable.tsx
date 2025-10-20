'use client'
import { useState, useRef, useEffect } from 'react'
import { Pencil, Trash2, X, Check, Download, ArrowUpDown, ArrowDown, ArrowUp, Table2 } from 'lucide-react'
import clsx from 'clsx'
import ProfessionalPagination from '../../components/ui/ProfessionalPagination'

type TableData = {
  header: string[]
  rows: string[][]
  name?: string
}

type ExtractedTablesProps = {
  tables: TableData[],
  onTablesChange?: (tables: TableData[]) => void,
  highlightedRow?: { tableIdx: number, rowIdx: number } | null,
  onRowHover?: (tableIdx: number, rowIdx: number | null) => void,
}

// Helper functions moved outside component
function isHeaderLikeRow(row: string[]) {
  const minStringCells = 3;
  const nonempty = row.filter(cell => cell && cell.trim());
  if (nonempty.length < minStringCells) return false;
  const allAlpha = nonempty.every(cell => /^[A-Za-z .\-:]+$/.test(cell.trim()));
  return allAlpha;
}

function fixPercent(val: string): string {
  if (!val) return val;
  return val
    .replace(/\bolo\b/g, '%')
    .replace(/\b010\b/g, '%')
    .replace(/OLO/g, '%')
    .replace(/010/g, '%');
}

function downloadCSV(table: TableData, name: string) {
  const csv = [
    table.header.join(','),
    ...table.rows.map(row => row.map(cell => '"' + (cell || '').replace(/"/g, '""') + '"').join(','))
  ].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (name || 'table') + '.csv';
  a.click();
  URL.revokeObjectURL(url);
}

const ROWS_OPTIONS = [10, 25, 50];


export default function ExtractedTables({ tables: backendTables, onTablesChange, highlightedRow, onRowHover }: ExtractedTablesProps) {
  // All hooks organized at the top - must be called before any early returns
  const [tab, setTab] = useState(0)
  const [tables, setTables] = useState(() => {
    // Backend now handles all table merging, so we just need to process the data
    return backendTables.map(table => ({
      ...table,
      rows: Array.isArray(table.rows) 
        ? [...table.rows] 
        : (typeof table.rows === 'object' && table.rows !== null)
          ? Object.values(table.rows) as string[][] // Convert object with numeric keys to array
          : [],
      name: table.name || ''
    }));
  })
  const [editRow, setEditRow] = useState<{ t: number, r: number } | null>(null)
  const [editValues, setEditValues] = useState<string[]>([])
  const [pages, setPages] = useState(Array(tables.length).fill(1))
  const [rowsPerPages, setRowsPerPages] = useState(Array(tables.length).fill(ROWS_OPTIONS[0]))
  const [selectedRows, setSelectedRows] = useState<Array<Set<number>>>(tables.map(() => new Set<number>()))
  const [sort, setSort] = useState<{ col: number, dir: 'asc' | 'desc' } | null>(null)
  const [colWidths, setColWidths] = useState<Array<number[]>>(tables.map(t => (t.header && Array.isArray(t.header) ? t.header.map(() => 160) : [])))
  
  // Refs
  const lastCallbackRef = useRef<string>('')
  const resizingCol = useRef<{ table: number, col: number } | null>(null)

  // Update local tables when backendTables change
  useEffect(() => {
    // Backend now handles all table merging, so we just need to process the data
    const processedTables: { rows: string[][]; name: string; header: string[]; }[] = backendTables.map(table => ({
      ...table,
      rows: Array.isArray(table.rows) 
        ? [...table.rows] 
        : (typeof table.rows === 'object' && table.rows !== null)
          ? Object.values(table.rows) as string[][] // Convert object with numeric keys to array
          : [],
      name: table.name || ''
    }));
    setTables(processedTables);
  }, [backendTables]);

  // Initialize state when tables change
  useEffect(() => {
    setSelectedRows(selRows => {
      if (tables.length === selRows.length) return selRows;
      return tables.map(() => new Set<number>());
    });
    setColWidths(widths => {
      if (tables.length === widths.length) return widths;
      return tables.map(t => (t.header && Array.isArray(t.header) ? t.header.map(() => 160) : []));
    });
    setTab(t => t >= tables.length ? 0 : t);
  }, [tables.length, tables]);

  // Call onTablesChange only when tables changes, but avoid infinite loops
  useEffect(() => {
    if (onTablesChange && tables.length > 0) {
      // Create a hash of the current tables to prevent unnecessary callbacks
      const tablesHash = JSON.stringify(tables.map(t => ({ header: t.header, rowCount: t.rows.length, name: t.name })));
      
      if (tablesHash !== lastCallbackRef.current) {
        lastCallbackRef.current = tablesHash;
        onTablesChange(tables);
      }
    }
  }, [tables, onTablesChange]);

  // Guard: If no tables or invalid tab, render nothing - AFTER all hooks
  if (!tables.length || !tables[tab] || !tables[tab].header || !Array.isArray(tables[tab].header)) return null;

  // Computed values
  const sortedRows = (() => {
    const currentTable = tables[tab];
    const rows = Array.isArray(currentTable.rows) ? currentTable.rows : [];
    
    if (!sort) return rows;
    const { col, dir } = sort;
    return [...rows].sort((a, b) => {
      const va = a[col] || '';
      const vb = b[col] || '';
      if (!isNaN(Number(va)) && !isNaN(Number(vb))) {
        return dir === 'asc' ? Number(va) - Number(vb) : Number(vb) - Number(va);
      }
      return dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    });
  })();

  const currentRowsPerPage = rowsPerPages[tab];
  const currentPage = pages[tab];
  const pageCount = Math.max(1, Math.ceil(sortedRows.length / currentRowsPerPage));
  const pagedRows = sortedRows.slice(
    (currentPage - 1) * currentRowsPerPage,
    currentPage * currentRowsPerPage
  );
  const globalIndices = Array.from({ length: pagedRows.length }, (_, i) => (currentPage - 1) * currentRowsPerPage + i);
  const totalItems = sortedRows.length;
  const showingFrom = (currentPage - 1) * currentRowsPerPage + 1;
  const showingTo = Math.min(currentPage * currentRowsPerPage, totalItems);

  // Event handlers
  function isRowSelected(idx: number) {
    return selectedRows[tab].has(idx);
  }

  function toggleRow(idx: number) {
    setSelectedRows(selRows =>
      selRows.map((s, i) => {
        if (i !== tab) return s;
        const newSet = new Set(s);
        if (newSet.has(idx)) newSet.delete(idx);
        else newSet.add(idx);
        return newSet;
      })
    )
  }

  function toggleSelectAllOnPage() {
    const selected = selectedRows[tab];
    const allSelected = globalIndices.every(idx => selected.has(idx));
    setSelectedRows(selRows =>
      selRows.map((s, i) => {
        if (i !== tab) return s;
        if (allSelected) {
          const newSet = new Set(s);
          globalIndices.forEach(idx => newSet.delete(idx));
          return newSet;
        } else {
          const newSet = new Set(s);
          globalIndices.forEach(idx => newSet.add(idx));
          return newSet;
        }
      })
    );
  }

  function deleteSelectedRowsOnPage() {
    setTables(tables =>
      tables.map((tbl, tblIdx) => {
        if (tblIdx !== tab) return tbl;
        const newRows = tbl.rows.filter((_, i) =>
          !selectedRows[tab].has(i)
        );
        return { ...tbl, rows: newRows }
      })
    );
    setSelectedRows(selRows =>
      selRows.map((s, i) => (i === tab ? new Set<number>() : s))
    );
    if (editRow?.t === tab && selectedRows[tab].has(editRow.r)) {
      setEditRow(null)
    }
  }

  function deleteRow(t: number, r: number) {
    setTables(tables =>
      tables.map((tbl, idx) =>
        idx === t ? { ...tbl, rows: tbl.rows.filter((_, i) => i !== r) } : tbl
      )
    )
    setSelectedRows(selRows =>
      selRows.map((s, i) => {
        if (i !== t) return s;
        const newSet = new Set(s);
        newSet.delete(r);
        return newSet;
      })
    );
    if (editRow?.t === t && editRow.r === r) setEditRow(null)
  }

  function startEdit(t: number, r: number) {
    setEditRow({ t, r })
    setEditValues([...tables[t].rows[r]])
  }

  function cancelEdit() {
    setEditRow(null)
    setEditValues([])
  }

  function saveEdit() {
    setTables(tables =>
      tables.map((tbl, tIdx) =>
        tIdx === editRow!.t
          ? { ...tbl, rows: tbl.rows.map((row, rIdx) => rIdx === editRow!.r ? editValues : row) }
          : tbl
      )
    )
    setEditRow(null)
    setEditValues([])
  }

  function onEditCell(i: number, v: string) {
    setEditValues(vals => vals.map((val, idx) => idx === i ? v : val))
  }

  function setPage(tabIdx: number, page: number) {
    setPages(pgs => pgs.map((p, idx) => idx === tabIdx ? page : p))
  }

  function setRowsPerPage(tabIdx: number, val: number) {
    setRowsPerPages(rpp => rpp.map((x, i) => i === tabIdx ? val : x))
    setPages(pgs => pgs.map((p, i) => (i === tabIdx ? 1 : p)));
  }

  function handleTableNameChange(idx: number, name: string) {
    setTables(tables => tables.map((t, i) => i === idx ? { ...t, name } : t));
  }

  function startResize(tableIdx: number, colIdx: number, e: React.MouseEvent) {
    resizingCol.current = { table: tableIdx, col: colIdx };
    document.body.style.cursor = 'col-resize';
    const startX = e.clientX;
    const startWidth = colWidths[tableIdx][colIdx];
    function onMove(ev: MouseEvent) {
      const delta = ev.clientX - startX;
      setColWidths(widths => widths.map((arr, t) => t === tableIdx ? arr.map((w, c) => c === colIdx ? Math.max(60, startWidth + delta) : w) : arr));
    }
    function onUp() {
      resizingCol.current = null;
      document.body.style.cursor = '';
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }

  function handleSort(colIdx: number) {
    setSort(s => {
      if (!s || s.col !== colIdx) return { col: colIdx, dir: 'asc' };
      if (s.dir === 'asc') return { col: colIdx, dir: 'desc' };
      return null;
    });
  }

  return (
    <div className="w-full">
      {/* Tabs for multiple tables */}
      <div className="flex space-x-2 border-b border-slate-200 mb-6 overflow-x-auto" role="tablist" aria-label="Extracted tables">
        {tables.map((tbl, idx) => (
          <div key={idx} className="relative flex items-center">
            <button
              className={clsx(
                "py-3 px-6 rounded-t-xl font-semibold transition-all flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-400",
                tab === idx
                  ? "bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              )}
              onClick={() => setTab(idx)}
              role="tab"
              aria-selected={tab === idx}
              aria-controls={`table-panel-${idx}`}
              tabIndex={0}
            >
              <Table2 size={18} />
              {tbl.name ? tbl.name : `Table ${idx + 1}`}
            </button>
            {/* Delete table button OUTSIDE the tab button */}
            {tables.length > 1 && (
              <button
                className="ml-2 text-red-500 hover:bg-red-100 rounded-lg p-1 absolute right-0 top-1/2 -translate-y-1/2 transition-colors"
                title="Delete this table"
                onClick={e => {
                  e.stopPropagation();
                  setTables(prevTables => {
                    const newTables = prevTables.filter((_, i) => i !== idx);
                    return newTables;
                  });
                }}
              >
                <X size={14} />
              </button>
            )}
          </div>
        ))}
        <button
          className="ml-auto px-4 py-2 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 flex items-center gap-2 text-sm font-medium transition-colors"
          onClick={() => downloadCSV(tables[tab], tables[tab].name || `table${tab + 1}`)}
          aria-label="Download as CSV"
        >
          <Download size={16} /> CSV
        </button>
      </div>
      {/* Table name input */}
      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm font-medium text-slate-700">Table Name (optional):</label>
        <input
          type="text"
          className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={tables[tab].name || ''}
          onChange={e => handleTableNameChange(tab, e.target.value)}
          placeholder={`Table ${tab + 1}`}
          aria-label="Table name"
        />
      </div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-4 px-2">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-slate-700">Rows per page:</label>
          <select
            value={currentRowsPerPage}
            onChange={e => setRowsPerPage(tab, Number(e.target.value))}
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-label="Rows per page"
          >
            {ROWS_OPTIONS.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
        <div className="text-sm text-slate-600">
          Showing <span className="font-semibold text-slate-800">{showingFrom}-{showingTo}</span> of <span className="font-semibold text-slate-800">{totalItems}</span> items
        </div>
        <button
          className={clsx(
            "flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200",
            (selectedRows[tab]?.size ?? 0) > 0 ? "hover:bg-red-600" : "opacity-50 cursor-not-allowed"
          )}
          disabled={(selectedRows[tab]?.size ?? 0) === 0}
          onClick={deleteSelectedRowsOnPage}
          aria-label="Delete selected rows"
        >
          <Trash2 size={16} />
          Delete selected
        </button>
      </div>
      <div className="rounded-xl border border-slate-200 shadow-lg overflow-x-auto bg-white">
        <table className="min-w-full company-table" role="table" aria-label={`Extracted table ${tab + 1}`}> 
          <thead className="bg-gradient-to-r from-slate-50 to-blue-50 sticky top-0 z-10">
            <tr>
              <th className="py-4 px-4 border-b border-slate-200 w-8 text-center sticky left-0 bg-gradient-to-r from-slate-50 to-blue-50 z-20">
                <input
                  type="checkbox"
                  className="accent-blue-600 w-4 h-4"
                  checked={globalIndices.length > 0 && globalIndices.every(isRowSelected)}
                  onChange={toggleSelectAllOnPage}
                  aria-label="Select all"
                />
              </th>
              {tables[tab].header.map((col, i) => (
                <th
                  key={i}
                  className="py-4 px-4 text-sm font-bold text-slate-800 border-b border-slate-200 sticky top-0 bg-gradient-to-r from-slate-50 to-blue-50 z-10 group"
                  style={{ minWidth: colWidths[tab][i], maxWidth: 400, position: 'relative' }}
                  tabIndex={0}
                  aria-sort={sort && sort.col === i ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
                >
                  <div className="flex items-center gap-2 cursor-pointer select-none" onClick={() => handleSort(i)}>
                    {fixPercent(col)}
                    {sort && sort.col === i ? (
                      sort.dir === 'asc' ? <ArrowUp size={16} className="text-blue-600" /> : <ArrowDown size={16} className="text-blue-600" />
                    ) : <ArrowUpDown size={14} className="opacity-40 group-hover:opacity-80 text-slate-500" />}
                  </div>
                  {/* Column resize handle */}
                  <span
                    className="absolute right-0 top-0 h-full w-2 cursor-col-resize z-30"
                    onMouseDown={e => startResize(tab, i, e)}
                    tabIndex={-1}
                    aria-label="Resize column"
                  />
                </th>
              ))}
              <th className="py-4 px-4 border-b border-slate-200 w-24 sticky right-0 bg-gradient-to-r from-slate-50 to-blue-50 z-20 text-slate-800 font-bold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {pagedRows.map((row, rIdx) => {
              const globalIdx = globalIndices[rIdx];
              const isEditing = editRow && editRow.t === tab && editRow.r === globalIdx;
              const headerLike = isHeaderLikeRow(row);
              const isHighlighted = highlightedRow && highlightedRow.tableIdx === tab && highlightedRow.rowIdx === globalIdx;
              if (headerLike) {
                return (
                  <tr key={globalIdx} className="bg-blue-50">
                    <th className="py-3 px-4 border-b border-slate-200 align-top"></th>
                    {row.map((val, i) => (
                      <th key={i} className="py-3 px-4 border-b border-slate-200 align-top font-bold text-slate-800">{val}</th>
                    ))}
                    <th className="py-3 px-4 border-b border-slate-200 align-top"></th>
                  </tr>
                );
              }
              return (
                <tr
                  key={globalIdx}
                  className={clsx(
                    isEditing ? "bg-blue-50" : isHighlighted ? "bg-amber-50 ring-2 ring-amber-400" : "hover:bg-slate-50",
                    "transition-colors"
                  )}
                  tabIndex={0}
                  aria-selected={isHighlighted ? 'true' : 'false'}
                  onMouseEnter={() => onRowHover && onRowHover(tab, globalIdx)}
                  onMouseLeave={() => onRowHover && onRowHover(tab, null)}
                >
                  <td className="py-3 px-4 border-b border-slate-200 align-top text-center sticky left-0 bg-white z-10">
                    <input
                      type="checkbox"
                      className="accent-blue-600 w-4 h-4"
                      checked={isRowSelected(globalIdx)}
                      onChange={() => toggleRow(globalIdx)}
                      aria-label={`Select row ${globalIdx + 1}`}
                    />
                  </td>
                  {row.map((val, i) => (
                    <td
                      key={i}
                      className="py-3 px-4 border-b border-slate-200 align-top"
                      style={{ minWidth: colWidths[tab][i], maxWidth: 400 }}
                    >
                      {isEditing
                        ? (
                          <input
                            value={editValues[i]}
                            onChange={e => onEditCell(i, e.target.value)}
                            className="border border-slate-200 rounded-lg px-3 py-1 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          />
                        )
                        : <span className="text-slate-800 text-sm">{fixPercent(val)}</span>
                      }
                    </td>
                  ))}
                  <td className="py-3 px-4 border-b border-slate-200 align-top sticky right-0 bg-white z-10">
                    {!isEditing ? (
                      <div className="flex gap-2">
                        <button className="p-2 text-blue-500 hover:bg-blue-50 rounded-lg transition-colors" onClick={() => startEdit(tab, globalIdx)} title="Edit" aria-label="Edit row">
                          <Pencil size={16} />
                        </button>
                        <button className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors" onClick={() => deleteRow(tab, globalIdx)} title="Delete" aria-label="Delete row">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors" onClick={saveEdit} title="Save" aria-label="Save edit">
                          <Check size={18} />
                        </button>
                        <button className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors" onClick={cancelEdit} title="Cancel" aria-label="Cancel edit">
                          <X size={18} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <ProfessionalPagination
        currentPage={currentPage}
        totalPages={pageCount}
        onPageChange={pg => setPage(tab, pg)}
      />
    </div>
  )
}
