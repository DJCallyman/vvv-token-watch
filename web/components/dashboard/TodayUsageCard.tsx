'use client'

import { useDailyUsage } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatNumber, formatCurrency, cn } from '@/lib/utils'
import { Activity, TrendingUp, TrendingDown } from 'lucide-react'

export function TodayUsageCard() {
  const { data: usage, isLoading, isError } = useDailyUsage()

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-48">
          <div className="animate-pulse text-muted-foreground">Loading...</div>
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

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  })

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="w-5 h-5" />
          Today&apos;s Usage
        </CardTitle>
        <p className="text-sm text-muted-foreground">{today}</p>
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
      </CardContent>
    </Card>
  )
}