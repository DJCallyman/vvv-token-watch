'use client'

import { AlertCircle, RefreshCw, SearchX } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from './button'
import { Skeleton } from './skeleton'

type DataStateProps = {
  kind: 'loading' | 'error' | 'empty' | 'stale'
  title: string
  description?: string
  onRetry?: () => void
  retryLabel?: string
  action?: ReactNode
  rows?: number
}

const SKELETON_IDS = ['one', 'two', 'three', 'four', 'five', 'six']

export function DataState({
  kind,
  title,
  description,
  onRetry,
  retryLabel = 'Retry',
  action,
  rows = 3,
}: DataStateProps) {
  if (kind === 'loading') {
    return (
      <div aria-live="polite" aria-busy="true" className="space-y-4 py-6">
        <span className="sr-only">{title}</span>
        <div className="space-y-2" aria-hidden="true">
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        <div className="space-y-3" aria-hidden="true">
          {SKELETON_IDS.slice(0, Math.max(0, rows)).map((skeletonId) => (
            <Skeleton key={skeletonId} className="h-12 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (kind === 'error') {
    return (
      <section role="alert" className="flex flex-col items-center gap-3 py-8 text-center">
        <AlertCircle className="h-6 w-6 text-destructive" aria-hidden="true" />
        <div className="space-y-1">
          <h2 className="text-base font-semibold">{title}</h2>
          {description && <p className="max-w-lg text-sm text-muted-foreground">{description}</p>}
        </div>
        {onRetry && (
          <Button type="button" variant="outline" onClick={onRetry}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            {retryLabel}
          </Button>
        )}
      </section>
    )
  }

  if (kind === 'stale') {
    return (
      <div aria-live="polite" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-warning/30 bg-warning/10 px-4 py-3">
        <div className="flex items-start gap-2">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
          <div className="space-y-1">
            <p className="text-sm font-medium">{title}</p>
            {description && <p className="text-sm text-muted-foreground">{description}</p>}
          </div>
        </div>
        {onRetry && (
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            {retryLabel}
          </Button>
        )}
      </div>
    )
  }

  return (
    <div aria-live="polite" aria-atomic="true" className="flex flex-col items-center gap-3 py-8 text-center">
      <SearchX className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      <div className="space-y-1">
        <h2 className="text-base font-semibold">{title}</h2>
        {description && <p className="max-w-lg text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  )
}