import type { BenchmarkRunDetail } from './api'

const TEST_IDS = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12']

function csvCell(value: unknown): string {
  const text = value == null ? '' : String(value)
  return `"${text.replace(/"/g, '""')}"`
}

function scoreFor(run: BenchmarkRunDetail, modelId: string, testId: string): number | string {
  const category = run.models.find((model) => model.model_id === modelId)?.categories?.[testId]
  return category?.score_effective ?? category?.score_mean ?? ''
}

export function benchmarkCsv(run: BenchmarkRunDetail): string {
  const headers = [
    'model_id',
    'composite_score',
    'data_coverage',
    ...TEST_IDS,
    'list_cost_usd',
    'billed_usd_equivalent',
    'judge_enabled',
    'judge_model',
  ]
  const rows = run.models.map((model) => [
    model.model_id,
    model.composite_score ?? '',
    model.data_coverage ?? '',
    ...TEST_IDS.map((testId) => scoreFor(run, model.model_id, testId)),
    model.costs?.total_cost_usd ?? '',
    model.actual_billed?.total_usd_equivalent ?? '',
    model.judge_enabled ? 'true' : 'false',
    model.judge_model ?? '',
  ])
  return [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\n') + '\n'
}

export function benchmarkMarkdown(run: BenchmarkRunDetail): string {
  const headers = ['Model', 'Composite', 'Coverage', ...TEST_IDS, 'List cost USD', 'Billed USD eq.', 'Judge']
  const divider = headers.map(() => '---')
  const rows = run.models.map((model) => [
    model.model_id,
    model.composite_score == null ? '' : model.composite_score.toFixed(3),
    model.data_coverage == null ? '' : `${(model.data_coverage * 100).toFixed(0)}%`,
    ...TEST_IDS.map((testId) => {
      const score = scoreFor(run, model.model_id, testId)
      return typeof score === 'number' ? score.toFixed(3) : ''
    }),
    model.costs?.total_cost_usd == null ? '' : model.costs.total_cost_usd.toFixed(6),
    model.actual_billed?.total_usd_equivalent == null ? '' : model.actual_billed.total_usd_equivalent.toFixed(6),
    model.judge_enabled ? model.judge_model ?? 'enabled' : 'off',
  ])
  const metadata = [
    `Generated: ${run.generated_at}`,
    `Models: ${run.model_count}`,
    `Judge: ${run.models.some((model) => model.judge_enabled) ? 'enabled' : 'off'}`,
  ].join('  \n')
  return `${metadata}\n\n| ${headers.join(' | ')} |\n| ${divider.join(' | ')} |\n${rows.map((row) => `| ${row.join(' | ')} |`).join('\n')}\n`
}

export function downloadBenchmarkFile(run: BenchmarkRunDetail, format: 'csv' | 'md'): void {
  const content = format === 'csv' ? benchmarkCsv(run) : benchmarkMarkdown(run)
  const mime = format === 'csv' ? 'text/csv;charset=utf-8' : 'text/markdown;charset=utf-8'
  const extension = format === 'csv' ? 'csv' : 'md'
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${run.run_id || 'benchmark'}.${extension}`
  link.click()
  URL.revokeObjectURL(url)
}
