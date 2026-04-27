'use client'

import { BenchmarkRunSummary } from '@/lib/api'

interface Props {
  runs: BenchmarkRunSummary[]
  selectedRunId: string | null
  onSelect: (runId: string) => void
  isLoading?: boolean
}

export function ResultsSelector({ runs, selectedRunId, onSelect, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="h-9 w-64 bg-muted/40 animate-pulse rounded-md" />
    )
  }

  if (!runs.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No benchmark results found. Run a benchmark to see results here.
      </p>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <label htmlFor="run-select" className="text-sm font-medium text-foreground whitespace-nowrap">
        Results set:
      </label>
      <select
        id="run-select"
        value={selectedRunId ?? ''}
        onChange={(e) => onSelect(e.target.value)}
        className="bg-card border border-border text-foreground text-sm rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary min-w-[280px]"
      >
        {runs.map((run) => (
          <option key={run.run_id} value={run.run_id}>
            {run.model_count} models — {run.timestamp}
          </option>
        ))}
      </select>
      <span className="text-xs text-muted-foreground">
        {runs.length} run{runs.length !== 1 ? 's' : ''} available
      </span>
    </div>
  )
}
