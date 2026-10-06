'use client'

import { useEvaluateSignal, useSignals } from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDateTime } from '@/lib/utils'
import { useDisplayPreferences } from '@/components/PreferencesProvider'
import { CheckCircle2, Clock, XCircle } from 'lucide-react'

function outcomeBadge(status: string) {
  if (status === 'hit') {
    return (
      <Badge variant="success" className="gap-1">
        <CheckCircle2 className="w-3 h-3" aria-hidden="true" /> Hit
      </Badge>
    )
  }
  if (status === 'miss') {
    return (
      <Badge variant="destructive" className="gap-1">
        <XCircle className="w-3 h-3" aria-hidden="true" /> Miss
      </Badge>
    )
  }
  return (
    <Badge variant="secondary" className="gap-1">
      <Clock className="w-3 h-3" aria-hidden="true" /> Pending
    </Badge>
  )
}

export function SignalHistory() {
  const { timezone } = useDisplayPreferences()
  const { data, isLoading, isError } = useSignals()
  const evaluate = useEvaluateSignal()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Signal History</CardTitle>
        <CardDescription>
          Structured AI signals with confidence and deterministic outcome tracking. Outcomes are
          evaluated against the latest VVV price when requested.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div aria-busy="true" className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        )}
        {isError && <p className="text-sm text-destructive">Failed to load signals</p>}
        {data && data.signals.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No signals recorded yet. Run an analysis or an X sentiment check.
          </p>
        )}
        <ul className="space-y-2">
          {data?.signals.map((signal) => (
            <li
              key={signal.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border p-3"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant={
                      signal.direction === 'bullish'
                        ? 'success'
                        : signal.direction === 'bearish'
                          ? 'destructive'
                          : 'secondary'
                    }
                  >
                    {signal.direction}
                  </Badge>
                  <span className="text-sm font-medium">{signal.confidence.toFixed(0)}% confidence</span>
                  <span className="text-xs text-muted-foreground">{signal.kind}</span>
                  {outcomeBadge(signal.outcome_status)}
                </div>
                {signal.rationale && (
                  <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{signal.rationale}</p>
                )}
                <p className="mt-1 text-xs text-muted-foreground">
                  {signal.created_at ? formatDateTime(signal.created_at, timezone) : '—'}
                  {signal.entry_price_usd != null
                    ? ` · entry $${signal.entry_price_usd.toFixed(4)}`
                    : ''}
                  {signal.outcome_value_usd != null
                    ? ` · current $${signal.outcome_value_usd.toFixed(4)}`
                    : ''}
                </p>
              </div>
              {signal.outcome_status === 'pending' && (
                <button
                  type="button"
                  onClick={() => evaluate.mutate({ id: signal.id })}
                  disabled={evaluate.isPending}
                  className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent disabled:opacity-50"
                >
                  Evaluate outcome
                </button>
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
