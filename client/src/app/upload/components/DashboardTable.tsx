'use client'
import { useState, useEffect } from 'react'
import { Pencil, Trash2, X, Check, Clock, Calendar } from 'lucide-react'
import clsx from 'clsx'
import ProfessionalPagination from '../../components/ui/ProfessionalPagination'

type TableData = {
  header: string[]
  rows: (string[] | Record<string, string>)[]
  name?: string // <-- add table name support
}

type FieldConfig = { field: string, label: string }

type DashboardTableProps = {
  tables: TableData[],
  fieldConfig: FieldConfig[],
  onEditMapping: () => void,
  company?: { id: string, name: string } | null,
  fileName?: string,
  fileUrl?: string | null,
  readOnly?: boolean,
  onTableChange?: (tables: TableData[]) => void,
  planTypes?: string[],
  onSendToPending?: () => void,
  uploadId?: string,
  selectedStatementDate?: any // Add selected statement date prop
}

function fixPercent(val: string): string {
  if (!val) return val
  return val
    .replace(/\bolo\b/g, '%')
    .replace(/\b010\b/g, '%')
    .replace(/OLO/g, '%')
    .replace(/010/g, '%')
}


const ROWS_OPTIONS = [10, 25, 50]

export default function DashboardTable({
  tables,
  fieldConfig,
  onEditMapping,
  company,
  fileName,
  fileUrl,
  readOnly = false,
  onTableChange,
  planTypes = [],
  onSendToPending,
  uploadId,
  selectedStatementDate, // Add selected statement date prop
}: DashboardTableProps) {

  
  // --- Main Table State (tracks edits/deletes) ---
  const [rows, setRows] = useState<TableData[]>(tables)
  // If `tables` prop changes (new upload, remap, etc), update local state
  useEffect(() => {
    setRows(tables)
  }, [tables])

  // Inform parent of any changes!
  useEffect(() => {
    if (onTableChange) onTableChange(rows)
    // eslint-disable-next-line
  }, [rows])

  // --- Flatten all tables into one long list with group headers ---
  type RowWithGroup = {
    type: 'header',
    groupIdx: number,
    header: string[],
    name?: string // <-- add name for group
  } | {
    type: 'row',
    groupIdx: number,
    row: string[] | Record<string, string>,
    globalRowIdx: number
  }
  const allRows: RowWithGroup[] = []
  let runningIdx = 0
  rows.forEach((table, groupIdx) => {
    allRows.push({ type: 'header', groupIdx, header: table.header, name: table.name })
    table.rows.forEach(row => {
      allRows.push({ type: 'row', groupIdx, row, globalRowIdx: runningIdx++ })
    })
  })

  // Pagination logic applies to only 'row' rows, not headers
  const dataRows = allRows.filter(r => r.type === 'row') as Extract<RowWithGroup, { type: 'row' }>[]
  const [page, setPage] = useState(1)
  const [rowsPerPage, setRowsPerPage] = useState(ROWS_OPTIONS[0])
  const pageCount = Math.max(1, Math.ceil(dataRows.length / rowsPerPage))
  const pagedDataRows = dataRows.slice((page - 1) * rowsPerPage, page * rowsPerPage)

  // To show headers with paginated rows, build a new "pagedRowsWithHeaders" array:
  const pagedRowsWithHeaders: RowWithGroup[] = []
  let lastGroupIdx: number | null = null
  pagedDataRows.forEach(row => {
    if (lastGroupIdx !== row.groupIdx) {
      pagedRowsWithHeaders.push({
        type: 'header',
        groupIdx: row.groupIdx,
        header: rows[row.groupIdx]?.header ?? [],
        name: rows[row.groupIdx]?.name
      })
      lastGroupIdx = row.groupIdx
    }
    pagedRowsWithHeaders.push(row)
  })

  // Selections tracked by globalRowIdx
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set())
  function isRowSelected(idx: number) {
    return selectedRows.has(idx)
  }
  function toggleRow(idx: number) {
    setSelectedRows(sel => {
      const next = new Set(sel)
      if (next.has(idx)) {
        next.delete(idx)
      } else {
        next.add(idx)
      }
      return next
    })
  }
  function toggleSelectAllOnPage() {
    const allSelected = pagedDataRows.every(row => isRowSelected(row.globalRowIdx))
    setSelectedRows(sel => {
      const next = new Set(sel)
      pagedDataRows.forEach(row => {
        if (allSelected) next.delete(row.globalRowIdx)
        else next.add(row.globalRowIdx)
      })
      return next
    })
  }
  function deleteSelectedRowsOnPage() {
    let rowIdx = 0
    const newTables = rows.map((table) => {
      const newRows = table.rows.filter(() => {
        const keep = !selectedRows.has(rowIdx)
        rowIdx++
        return keep
      })
      return { ...table, rows: newRows }
    })
    setSelectedRows(new Set())
    setPage(1)
    setRows(newTables)
  }
  function deleteRow(globalRowIdx: number) {
    let idx = 0
    const newTables = rows.map(table => {
      const newRows = table.rows.filter(() => {
        if (idx === globalRowIdx) {
          idx++
          return false
        }
        idx++
        return true
      })
      return { ...table, rows: newRows }
    })
    setRows(newTables)
    setSelectedRows(sel => {
      const next = new Set(sel)
      next.delete(globalRowIdx)
      return next
    })
    setPage(1)
  }

  // Editing logic
  const [editRowIdx, setEditRowIdx] = useState<number | null>(null)
  const [editValues, setEditValues] = useState<string[]>([])
  function startEdit(globalRowIdx: number) {
    setEditRowIdx(globalRowIdx)
    let idx = 0
    let foundRow: string[] | Record<string, string> = []
    rows.forEach(table => {
      table.rows.forEach(row => {
        if (idx === globalRowIdx) foundRow = row
        idx++
      })
    })
    
    // Convert to array format for editing
    if (Array.isArray(foundRow)) {
      setEditValues([...foundRow])
    } else {
      // Convert object to array based on fieldConfig
      const values = fieldConfig.map(field => (foundRow as Record<string, string>)[field.field] || '')
      setEditValues(values)
    }
  }
  function cancelEdit() {
    setEditRowIdx(null)
    setEditValues([])
  }
  function saveEdit() {
    let idx = 0
    const newTables = rows.map(table => {
      const newRows = table.rows.map((row) => {
        if (idx === editRowIdx) {
          idx++
          // If original row was an object, convert editValues back to object format
          if (!Array.isArray(row)) {
            const updatedRow: Record<string, string> = {}
            fieldConfig.forEach((field, index) => {
              updatedRow[field.field] = editValues[index] || ''
            })
            return updatedRow
          }
          return editValues
        }
        idx++
        return row
      })
      return { ...table, rows: newRows }
    })
    setRows(newTables)
    setEditRowIdx(null)
    setEditValues([])
  }
  function onEditCell(i: number, v: string) {
    setEditValues(vals => vals.map((val, idx) => idx === i ? v : val))
  }

  // Show message if empty
  const allDataRows = rows.flatMap(t => t.rows)
  if (!allDataRows.length) {
    return <div className="text-gray-500 text-center my-10">No dashboard data found in the extracted table.</div>
  }

  return (
    <div className="shadow-lg rounded-2xl p-6 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-x-auto w-full h-full flex flex-col">
      {planTypes && planTypes.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-3 items-center">
          <span className="font-semibold text-slate-700 dark:text-slate-300 text-base">Plan Types:</span>
          {planTypes.map(pt => (
            <span key={pt} className="inline-block px-4 py-2 rounded-lg bg-blue-50 text-blue-700 font-medium text-sm border border-blue-200">
              {pt.charAt(0).toUpperCase() + pt.slice(1)}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-4 px-2">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Rows per page:</label>
          <select
            value={rowsPerPage}
            onChange={e => { setRowsPerPage(Number(e.target.value)); setPage(1) }}
            className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {ROWS_OPTIONS.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
        <div className="text-sm text-slate-600 dark:text-slate-400">
          Showing <span className="font-semibold text-slate-800 dark:text-slate-200">{(page - 1) * rowsPerPage + 1}-{Math.min(page * rowsPerPage, dataRows.length)}</span> of <span className="font-semibold text-slate-800 dark:text-slate-200">{dataRows.length}</span> items
        </div>
        {!readOnly && (
          <div className="flex items-center gap-3">
            <button
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200",
                selectedRows.size > 0 ? "hover:bg-red-600" : "opacity-50 cursor-not-allowed"
              )}
              disabled={selectedRows.size === 0}
              onClick={deleteSelectedRowsOnPage}
            >
              <Trash2 size={16} />
              Delete selected
            </button>
            <button
              onClick={onEditMapping}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
            >
              Edit Field Mapping
            </button>
            {onSendToPending && (
              <button
                onClick={onSendToPending}
                className="px-4 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-orange-600 text-white font-semibold shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 flex items-center gap-2"
              >
                <Clock size={16} />
                Send to Pending
              </button>
            )}
          </div>
        )}
       
      </div>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full company-table">
        <thead className="bg-gradient-to-r from-slate-50 to-blue-50 dark:from-slate-700 dark:to-slate-600 sticky top-0">
          {/* Render table name row only above the corresponding table's header */}
          {pagedRowsWithHeaders.map((item, i) => {
            if (item.type === 'header' && item.name) {
              return (
                <tr key={`name-${item.groupIdx}-${i}`}>
                  <td colSpan={fieldConfig.length + (!readOnly ? 2 : 1)} className="py-3 px-4 text-lg font-bold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/30 border-b border-slate-200 dark:border-slate-600 text-center">
                    {item.name}
                  </td>
                </tr>
              )
            }
            return null;
          })}
          <tr>
            {!readOnly && (
              <th className="py-4 px-4 border-b border-slate-200 dark:border-slate-600 w-8 text-center">
                <input
                  type="checkbox"
                  className="accent-blue-600 w-4 h-4"
                  checked={pagedDataRows.length > 0 && pagedDataRows.every(row => isRowSelected(row.globalRowIdx))}
                  onChange={toggleSelectAllOnPage}
                  aria-label="Select all on page"
                />
              </th>
            )}
            {fieldConfig && fieldConfig.length > 0 ? (
              fieldConfig.map((f, idx) => (
                <th key={f.field || idx} className="px-4 py-4 text-left font-bold text-slate-800 dark:text-slate-200 border-b border-slate-200 dark:border-slate-600">
                  {f.label}
                </th>
              ))
            ) : (
              // Fallback headers when fieldConfig is not available
              rows[0]?.header?.map((header, idx) => (
                <th key={idx} className="px-4 py-4 text-left font-bold text-slate-800 dark:text-slate-200 border-b border-slate-200 dark:border-slate-600">
                  {header}
                </th>
              )) || []
            )}
            {!readOnly && <th className="py-4 px-4 border-b border-slate-200 dark:border-slate-600 w-40 text-slate-800 dark:text-slate-200 font-bold">Actions</th>}
          </tr>
        </thead>
        <tbody>
         
          {pagedRowsWithHeaders.map((item, i) => {
            if (item.type === 'row') {
              const row = item.row
              const globalIdx = item.globalRowIdx
              const isEditing = editRowIdx === globalIdx
              return (
                <tr key={globalIdx} className={isEditing ? "bg-blue-50 dark:bg-blue-900/20" : "hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"}>
                  {!readOnly && (
                    <td className="py-3 px-4 border-b border-slate-200 dark:border-slate-600 align-top text-center">
                      <input
                        type="checkbox"
                        className="accent-blue-600 w-4 h-4"
                        checked={isRowSelected(globalIdx)}
                        onChange={() => toggleRow(globalIdx)}
                        aria-label={`Select row ${globalIdx + 1}`}
                      />
                    </td>
                  )}
                  {Array.isArray(row) 
                    ? row.map((val: string, colIdx: number) => (
                        <td key={colIdx} className="py-3 px-4 border-b border-slate-200 dark:border-slate-600 align-top">
                          {isEditing
                            ? (
                              <input
                                value={editValues[colIdx] ?? ""}
                                onChange={e => onEditCell(colIdx, e.target.value)}
                                className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-1 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                              />
                            )
                            : (
                              (val && val.trim())
                                ? <span className="text-slate-800 dark:text-slate-200 text-sm">{fixPercent(val)}</span>
                                : <span className="text-slate-400 dark:text-slate-500">-</span>
                            )
                          }
                        </td>
                      ))
                    : fieldConfig.map((field, colIdx) => (
                        <td key={colIdx} className="py-3 px-4 border-b border-slate-200 dark:border-slate-600 align-top">
                          {isEditing
                            ? (
                              <input
                                value={editValues[colIdx] ?? ""}
                                onChange={e => onEditCell(colIdx, e.target.value)}
                                className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-1 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                              />
                            )
                            : (
                              (() => {
                                const val = (row as Record<string, string>)[field.field] || '';
                                return (val && val.trim())
                                  ? <span className="text-slate-800 text-sm">{fixPercent(val)}</span>
                                  : <span className="text-slate-400">-</span>;
                              })()
                            )
                          }
                        </td>
                      ))
                  }
                  {!readOnly && (
                    <td className="py-3 px-4 border-b border-slate-200 dark:border-slate-600 align-top">
                      {!isEditing ? (
                        <div className="flex gap-2">
                          <button className="p-2 text-blue-500 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors" onClick={() => startEdit(globalIdx)} title="Edit">
                            <Pencil size={16} />
                          </button>
                          <button className="p-2 text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors" onClick={() => deleteRow(globalIdx)} title="Delete">
                            <Trash2 size={16} />
                          </button>
                        </div>
                      ) : (
                        <div className="flex gap-2">
                          <button className="p-2 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-lg transition-colors" onClick={saveEdit} title="Save">
                            <Check size={18} />
                          </button>
                          <button className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors" onClick={cancelEdit} title="Cancel">
                            <X size={18} />
                          </button>
                        </div>
                      )}
                    </td>
                  )}
                </tr>
              )
            }
            return null
          })}
        </tbody>
      </table>
      </div>
      <div className="mt-4">
        <ProfessionalPagination
          currentPage={page}
          totalPages={pageCount}
          onPageChange={setPage}
        />
      </div>
    </div>
  )
}
