'use client'

import { useEpochUsage } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDateTime, formatNumber, formatCurrency } from '@/lib/utils'
import { Activity } from 'lucide-react'
import { useDisplayPreferences } from '@/components/PreferencesProvider'

export function TodayUsageCard() {
  const { data: usage, isLoading, isError } = useEpochUsage()
  const { timezone } = useDisplayPreferences()

  if (isLoading) {
    return (
      <Card aria-busy="true" aria-live="polite" className="h-full">
        <span className="sr-only">Loading epoch usage</span>
        <CardHeader className="pb-2 space-y-2">
          <Skeleton aria-hidden="true" className="h-6 w-44" />
          <Skeleton aria-hidden="true" className="h-3 w-36" />
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Skeleton aria-hidden="true" className="h-3 w-24" />
            <Skeleton aria-hidden="true" className="h-8 w-36" />
          </div>
          <div className="space-y-2">
            <Skeleton aria-hidden="true" className="h-3 w-24" />
            <Skeleton aria-hidden="true" className="h-8 w-36" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (isError || !usage) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-48">
          <div className="text-destructive">Failed to load usage</div>
        </CardContent>
      </Card>
    )
  }

  const epochStart = usage.epoch_start ? formatDateTime(usage.epoch_start, timezone) : null

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="w-5 h-5" />
          This Epoch&apos;s Usage
        </CardTitle>
        {epochStart && (
          <p className="text-xs text-muted-foreground">Since {epochStart}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <p className="text-sm text-muted-foreground">DIEM Consumed</p>
          <p className="text-3xl font-bold text-foreground">
            {formatNumber(usage.diem, 4)}
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">USD Consumed</p>
          <p className="text-3xl font-bold text-foreground">
            {formatCurrency(usage.usd)}
          </p>
        </div>
        {(usage.bundled_credits > 0 || usage.earned_credits > 0) && (
          <div className="grid grid-cols-2 gap-4 border-t border-border pt-4">
            {usage.bundled_credits > 0 && (
              <div>
                <p className="text-xs text-muted-foreground">Bundled credits</p>
                <p className="text-lg font-semibold">{formatNumber(usage.bundled_credits, 4)}</p>
              </div>
            )}
            {usage.earned_credits > 0 && (
              <div>
                <p className="text-xs text-muted-foreground">Earned credits</p>
                <p className="text-lg font-semibold">{formatNumber(usage.earned_credits, 4)}</p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}