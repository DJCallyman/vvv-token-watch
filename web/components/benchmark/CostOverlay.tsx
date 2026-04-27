'use client'

import { useMemo } from 'react'
import { BenchmarkModelResult } from '@/lib/api'

interface Props {
  models: BenchmarkModelResult[]
}

export function CostOverlay({ models }: Props) {
  const ranked = useMemo(() => {
    return models
      .filter((m) => {
        const score = m.composite_score
        const cost = m.model_meta?.pricing_input_usd
        return score != null && cost != null && cost > 0
      })
      .map((m) => ({
        model_id: m.model_id,
        composite_score: m.composite_score!,
        pricing_input_usd: m.model_meta.pricing_input_usd!,
        pricing_output_usd: m.model_meta.pricing_output_usd,
        value_score: m.composite_score! / m.model_meta.pricing_input_usd!,
      }))
      .sort((a, b) => b.value_score - a.value_score)
      .slice(0, 15)
  }, [models])

  const maxValue = ranked[0]?.value_score ?? 1

  if (!ranked.length) {
    return (
      <p className="text-sm text-muted-foreground mt-2">
        No pricing data available for value comparison.
      </p>
    )
  }

  return (
    <div className="mt-4 p-4 bg-card rounded-lg border border-border">
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Best Value for Money
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Composite score ÷ input cost per 1M tokens. Higher = more performance per dollar.
      </p>
      <div className="space-y-2">
        {ranked.map((m, idx) => {
          const barPct = (m.value_score / maxValue) * 100
          const isTop3 = idx < 3
          return (
            <div key={m.model_id} className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-5 tabular-nums text-right shrink-0">
                {idx + 1}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span
                    className="text-xs font-mono text-foreground truncate"
                    title={m.model_id}
                  >
                    {m.model_id}
                  </span>
                  <span className="text-xs text-muted-foreground shrink-0 ml-2 tabular-nums">
                    score {m.composite_score.toFixed(1)} · ${m.pricing_input_usd.toFixed(2)}/1M
                  </span>
                </div>
                <div className="h-1.5 bg-muted/40 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      isTop3 ? 'bg-primary' : 'bg-muted-foreground/40'
                    }`}
                    style={{ width: `${barPct}%` }}
                  />
                </div>
              </div>
              <span className={`text-xs tabular-nums shrink-0 w-16 text-right ${isTop3 ? 'text-primary font-semibold' : 'text-muted-foreground'}`}>
                {m.value_score.toFixed(1)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
