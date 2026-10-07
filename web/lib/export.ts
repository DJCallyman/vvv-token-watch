// Client-side export helpers (Phase 4): CSV, JSON, and snapshot downloads.

export type ExportRow = Record<string, unknown>

/** Escape one CSV cell per RFC 4180. */
export function csvCell(value: unknown): string {
  if (value == null) return ''
  const text = typeof value === 'object' ? JSON.stringify(value) : String(value)
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`
  }
  return text
}

/**
 * Serialize rows to CSV. The header is the union of keys in first-seen order
 * so heterogeneous rows never drop columns silently.
 */
export function toCsv(rows: ExportRow[]): string {
  if (rows.length === 0) return ''
  const headers: string[] = []
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (!headers.includes(key)) headers.push(key)
    }
  }
  const lines = [headers.map(csvCell).join(',')]
  for (const row of rows) {
    lines.push(headers.map((header) => csvCell(row[header])).join(','))
  }
  return lines.join('\n')
}

export function toPrettyJson(data: unknown): string {
  return JSON.stringify(data, null, 2)
}

export function snapshotFilename(prefix: string, now: Date = new Date()): string {
  const stamp = now.toISOString().replace(/[:.]/g, '-')
  return `${prefix}-${stamp}.json`
}

export function csvFilename(prefix: string, now: Date = new Date()): string {
  const stamp = now.toISOString().slice(0, 10)
  return `${prefix}-${stamp}.csv`
}

/** Trigger a browser download. No-op in non-browser environments. */
export function downloadFile(filename: string, content: string, mime: string): void {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function exportJson(filename: string, data: unknown): void {
  downloadFile(filename, toPrettyJson(data), 'application/json')
}

export function exportCsv(filename: string, rows: ExportRow[]): void {
  downloadFile(filename, toCsv(rows), 'text/csv')
}

export function buildSnapshot(generatedAt: string, data: Record<string, unknown>): Record<string, unknown> {
  return {
    app: 'vvv-token-watch',
    snapshot_version: 1,
    generated_at: generatedAt,
    data,
  }
}
