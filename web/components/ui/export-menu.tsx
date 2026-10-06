'use client'

import { FileJson, FileSpreadsheet } from 'lucide-react'
import {
  buildSnapshot,
  exportCsv,
  exportJson,
  snapshotFilename,
  csvFilename,
  type ExportRow,
} from '@/lib/export'

interface ExportMenuProps {
  /** Filename prefix, e.g. "usage". */
  name: string
  /** Returns the JSON snapshot payload (called on click). */
  snapshot: () => Record<string, unknown>
  /** Optional rows for CSV export. */
  rows?: () => ExportRow[]
  className?: string
}

export function ExportMenu({ name, snapshot, rows, className }: ExportMenuProps) {
  return (
    <div className={`flex items-center gap-2 ${className ?? ''}`}>
      <button
        type="button"
        onClick={() =>
          exportJson(snapshotFilename(name), buildSnapshot(new Date().toISOString(), snapshot()))
        }
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label={`Export ${name} snapshot as JSON`}
      >
        <FileJson className="w-3.5 h-3.5" aria-hidden="true" />
        JSON
      </button>
      {rows && (
        <button
          type="button"
          onClick={() => exportCsv(csvFilename(name), rows())}
          className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={`Export ${name} rows as CSV`}
        >
          <FileSpreadsheet className="w-3.5 h-3.5" aria-hidden="true" />
          CSV
        </button>
      )}
    </div>
  )
}
