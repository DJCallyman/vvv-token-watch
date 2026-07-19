'use client'

import { useState, useMemo } from 'react'
import { BenchmarkRunDetail, BenchmarkModelResult } from '@/lib/api'

const TEST_IDS = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8']
const TEST_LABELS: Record<string, string> = {
  T1: 'Latency',
  T2: 'Tools',
  T3: 'Schema',
  T4: 'Instruct',
  T5: 'Reason',
  T6: 'Context',
  T7: 'Consist.',
  T8: 'Concise',
}

type SortKey = 'composite_score' | 'data_coverage' | 'pricing_input_usd' | 'pricing_output_usd' | 'value_score' | 'actual_cost' | 'billed_usd' | string

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null || score === undefined) {
    return <span className="text-muted-foreground text-xs">—</span>
  }
  const pct = Math.round(score * 100)
  const cls =
    pct >= 80
      ? 'bg-green-900/60 text-green-300'
      : pct >= 50
      ? 'bg-amber-900/60 text-amber-300'
      : 'bg-red-900/60 text-red-300'
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-mono tabular-nums ${cls}`}>
      {pct}
    </span>
  )
}

function CompositeScore({ score }: { score: number | null }) {
  if (score === null || score === undefined) {
    return <span className="text-muted-foreground text-xs">—</span>
  }
  const cls =
    score >= 80
      ? 'text-green-400 font-semibold'
      : score >= 50
      ? 'text-amber-400 font-semibold'
      : 'text-red-400 font-semibold'
  return <span className={`text-sm font-mono tabular-nums ${cls}`}>{score.toFixed(1)}</span>
}

function SortHeader({
  label,
  sortKey,
  currentKey,
  dir,
  onClick,
}: {
  label: string
  sortKey: SortKey
  currentKey: SortKey
  dir: 'asc' | 'desc'
  onClick: (k: SortKey) => void
}) {
  const active = currentKey === sortKey
  return (
    <th
      className="px-2 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide cursor-pointer select-none hover:text-foreground transition-colors whitespace-nowrap"
      onClick={() => onClick(sortKey)}
    >
      {label}
      {active && <span className="ml-1 text-primary">{dir === 'desc' ? '▼' : '▲'}</span>}
    </th>
  )
}

function formatPrice(val: number | null): string {
  if (val === null || val === undefined) return '—'
  return `$${val.toFixed(2)}`
}

function formatCost(val: number | null): string {
  if (val === null || val === undefined) return '—'
  if (val >= 1) return `$${val.toFixed(2)}`
  if (val >= 0.01) return `$${val.toFixed(3)}`
  return `$${val.toFixed(6)}`
}

function computeValueScore(model: BenchmarkModelResult): number {
  const score = model.composite_score
  const cost = model.model_meta?.pricing_input_usd
  if (!score || !cost || cost <= 0) return -1
  return score / cost
}

interface Props {
  runDetail: BenchmarkRunDetail
}

export function ResultsTable({ runDetail }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('composite_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [showCosts, setShowCosts] = useState(false)

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      // Cost columns sort ascending by default (cheaper = better), others descending
      setSortDir(['pricing_input_usd', 'pricing_output_usd', 'actual_cost', 'billed_usd'].includes(key) ? 'asc' : 'desc')
    }
  }

  const getSortValue = (model: BenchmarkModelResult): number => {
    if (sortKey === 'composite_score') return model.composite_score ?? -1
    if (sortKey === 'data_coverage') return model.data_coverage ?? 0
    if (sortKey === 'pricing_input_usd') return model.model_meta?.pricing_input_usd ?? 9999
    if (sortKey === 'pricing_output_usd') return model.model_meta?.pricing_output_usd ?? 9999
    if (sortKey === 'value_score') return computeValueScore(model)
    if (sortKey === 'actual_cost') return model.costs?.total_cost_usd ?? 9999
    if (sortKey === 'billed_usd') return model.actual_billed?.total_usd ?? 9999
    // Test column
    const cat = model.categories?.[sortKey]
    if (!cat) return -1
    return cat.score_effective ?? cat.score_mean ?? -1
  }

  const sortedModels = useMemo(() => {
    return [...runDetail.models].sort((a, b) => {
      const av = getSortValue(a)
      const bv = getSortValue(b)
      return sortDir === 'desc' ? bv - av : av - bv
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runDetail.models, sortKey, sortDir])

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-muted-foreground">
          {runDetail.model_count} models · click column headers to sort
        </p>
        <button
          onClick={() => setShowCosts((v) => !v)}
          className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
            showCosts
              ? 'bg-primary text-primary-foreground border-primary'
              : 'bg-card text-muted-foreground border-border hover:text-foreground'
          }`}
        >
          {showCosts ? 'Hide Costs' : 'Show Costs'}
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/30 border-b border-border sticky top-0">
            <tr>
              <th className="px-2 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide w-10">#</th>
              <SortHeader label="Model" sortKey="model_id" currentKey={sortKey} dir={sortDir} onClick={handleSort} />
              <SortHeader label="Score" sortKey="composite_score" currentKey={sortKey} dir={sortDir} onClick={handleSort} />
              <SortHeader label="Cov." sortKey="data_coverage" currentKey={sortKey} dir={sortDir} onClick={handleSort} />
              {TEST_IDS.map((tid) => (
                <SortHeader key={tid} label={TEST_LABELS[tid]} sortKey={tid} currentKey={sortKey} dir={sortDir} onClick={handleSort} />
              ))}
              {showCosts && (
                <>
                  <SortHeader label="In $/1M" sortKey="pricing_input_usd" currentKey={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="Out $/1M" sortKey="pricing_output_usd" currentKey={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="List Cost" sortKey="actual_cost" currentKey={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="Billed" sortKey="billed_usd" currentKey={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="Score/$" sortKey="value_score" currentKey={sortKey} dir={sortDir} onClick={handleSort} />
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {sortedModels.map((model, idx) => {
              const valueScore = computeValueScore(model)
              return (
                <tr
                  key={model.model_id}
                  className="border-b border-border/50 hover:bg-muted/20 transition-colors"
                >
                  <td className="px-2 py-1.5 text-xs text-muted-foreground tabular-nums">{idx + 1}</td>
                  <td className="px-2 py-1.5 font-mono text-xs text-foreground max-w-[180px] truncate" title={model.model_id}>
                    {model.model_id}
                  </td>
                  <td className="px-2 py-1.5">
                    <CompositeScore score={model.composite_score} />
                  </td>
                  <td className="px-2 py-1.5 text-xs text-muted-foreground tabular-nums">
                    {model.data_coverage != null ? `${Math.round(model.data_coverage * 100)}%` : '—'}
                  </td>
                  {TEST_IDS.map((tid) => {
                    const cat = model.categories?.[tid]
                    const score = cat?.score_effective ?? cat?.score_mean ?? null
                    return (
                      <td key={tid} className="px-2 py-1.5 text-center">
                        {cat?.skipped ? (
                          <span className="text-muted-foreground/50 text-xs">skip</span>
                        ) : (
                          <ScoreBadge score={score} />
                        )}
                      </td>
                    )
                  })}
                  {showCosts && (
                    <>
                      <td className="px-2 py-1.5 text-xs text-muted-foreground tabular-nums">
                        {formatPrice(model.model_meta?.pricing_input_usd)}
                      </td>
                      <td className="px-2 py-1.5 text-xs text-muted-foreground tabular-nums">
                        {formatPrice(model.model_meta?.pricing_output_usd)}
                      </td>
                      <td className="px-2 py-1.5 text-xs text-muted-foreground tabular-nums" title={`${model.costs?.total_cost_per_run_usd ?? '—'} per run`}>
                        {formatCost(model.costs?.total_cost_usd ?? null)}
                      </td>
                      <td className="px-2 py-1.5 text-xs text-muted-foreground tabular-nums" title={`${model.actual_billed?.categories ? Object.values(model.actual_billed.categories).map(c => c.billed_per_run_usd_equivalent).filter(Boolean).join(', ') : '—'} per run`}>
                        {formatCost(model.actual_billed?.total_usd_equivalent ?? null)}
                      </td>
                      <td className="px-2 py-1.5 text-xs text-muted-foreground tabular-nums">
                        {valueScore > 0 ? valueScore.toFixed(1) : '—'}
                      </td>
                    </>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
