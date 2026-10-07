'use client'

import { useEffect, useId, useMemo, useState, type ReactNode } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, SlidersHorizontal } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './table'

export interface DataTableColumn<T> {
  id: string
  header: string
  cell: (row: T) => ReactNode
  sortValue?: (row: T) => string | number | null | undefined
  className?: string
  hideable?: boolean
}

interface DataTableProps<T> {
  rows: T[]
  columns: DataTableColumn<T>[]
  getRowId: (row: T) => string
  ariaLabel: string
  emptyMessage: string
  initialSort?: { columnId: string; direction: 'asc' | 'desc' }
  initialPageSize?: number
}

type SortState = { columnId: string; direction: 'asc' | 'desc' } | null

function compareValues(left: string | number | null | undefined, right: string | number | null | undefined): number {
  if (left == null) return right == null ? 0 : -1
  if (right == null) return 1
  if (typeof left === 'number' && typeof right === 'number') return left - right
  return String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: 'base' })
}

export function DataTable<T>({
  rows,
  columns,
  getRowId,
  ariaLabel,
  emptyMessage,
  initialSort,
  initialPageSize = 10,
}: DataTableProps<T>) {
  const [sort, setSort] = useState<SortState>(initialSort ?? null)
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(initialPageSize)
  const [visibleColumnIds, setVisibleColumnIds] = useState(() => columns.map((column) => column.id))
  const pageSizeId = useId()

  const visibleColumns = columns.filter((column) => visibleColumnIds.includes(column.id))
  const sortedRows = useMemo(() => {
    if (!sort) return rows
    const column = columns.find((candidate) => candidate.id === sort.columnId)
    if (!column?.sortValue) return rows
    const direction = sort.direction === 'asc' ? 1 : -1
    return [...rows].sort((left, right) => direction * compareValues(column.sortValue?.(left), column.sortValue?.(right)))
  }, [columns, rows, sort])

  const pageCount = Math.max(1, Math.ceil(sortedRows.length / pageSize))
  const currentPage = Math.min(page, pageCount - 1)
  const pageRows = sortedRows.slice(currentPage * pageSize, (currentPage + 1) * pageSize)

  useEffect(() => {
    if (page !== currentPage) setPage(currentPage)
  }, [currentPage, page])

  const toggleSort = (column: DataTableColumn<T>) => {
    if (!column.sortValue) return
    setPage(0)
    setSort((current) => ({
      columnId: column.id,
      direction: current?.columnId === column.id && current.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const toggleColumn = (columnId: string) => {
    setVisibleColumnIds((current) => {
      if (current.includes(columnId)) {
        if (current.length === 1) return current
        return current.filter((id) => id !== columnId)
      }
      return [...current, columnId]
    })
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-4">
        <details className="relative">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-2 rounded-md border border-border px-3 text-sm text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
            Columns
          </summary>
          <fieldset className="absolute left-0 top-12 z-20 min-w-44 space-y-2 rounded-md border border-border bg-card p-3 shadow-md">
            <legend className="sr-only">Visible table columns</legend>
            {columns.filter((column) => column.hideable !== false).map((column) => (
              <label key={column.id} className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={visibleColumnIds.includes(column.id)}
                  onChange={() => toggleColumn(column.id)}
                />
                {column.header}
              </label>
            ))}
          </fieldset>
        </details>
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <label htmlFor={pageSizeId}>Rows</label>
          <select
              id={pageSizeId}
            aria-label="Rows per page"
            value={pageSize}
            onChange={(event) => {
              setPageSize(Number(event.target.value))
              setPage(0)
            }}
            className="h-10 rounded-md border border-input bg-background px-2 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {[10, 25, 50].map((size) => <option key={size} value={size}>{size}</option>)}
          </select>
        </div>
      </div>

      <Table aria-label={ariaLabel}>
        <TableHeader>
          <TableRow>
            {visibleColumns.map((column) => {
              const sortDirection = sort?.columnId === column.id ? sort.direction : null
              const SortIcon = sortDirection === 'asc' ? ArrowUp : sortDirection === 'desc' ? ArrowDown : ArrowUpDown
              return (
                <TableHead key={column.id} aria-sort={sortDirection === 'asc' ? 'ascending' : sortDirection === 'desc' ? 'descending' : 'none'} className={column.className}>
                  {column.sortValue ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(column)}
                      className="inline-flex min-h-10 items-center gap-2 rounded-sm text-left hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      {column.header}
                      <SortIcon className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  ) : column.header}
                </TableHead>
              )
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {pageRows.length ? pageRows.map((row) => (
            <TableRow key={getRowId(row)}>
              {visibleColumns.map((column) => (
                <TableCell key={column.id} className={column.className}>{column.cell(row)}</TableCell>
              ))}
            </TableRow>
          )) : (
            <TableRow>
              <TableCell colSpan={Math.max(visibleColumns.length, 1)} className="py-8 text-center text-muted-foreground">
                {emptyMessage}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <nav aria-label={`${ariaLabel} pagination`} className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground" aria-live="polite">
          {sortedRows.length === 0 ? '0 rows' : `${currentPage * pageSize + 1}–${Math.min((currentPage + 1) * pageSize, sortedRows.length)} of ${sortedRows.length}`}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Previous page"
            onClick={() => setPage((current) => Math.max(0, current - 1))}
            disabled={currentPage === 0}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </button>
          <span className="min-w-16 text-center text-sm tabular-nums">{currentPage + 1} / {pageCount}</span>
          <button
            type="button"
            aria-label="Next page"
            onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))}
            disabled={currentPage >= pageCount - 1}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </nav>
    </div>
  )
}