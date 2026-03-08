'use client'

import { useAPIKeysUsage, useDailyUsage } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { formatNumber, formatCurrency, formatDate } from '@/lib/utils'
import { BarChart3, Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react'

export function UsageView() {
  const { data: usage, isLoading: usageLoading } = useDailyUsage()
  const { data: keysUsage, isLoading: keysLoading } = useAPIKeysUsage()

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  const isLoading = usageLoading || keysLoading

  const totalKeys = keysUsage?.keys?.length || 0
  const activeKeys = keysUsage?.keys?.filter(k => k.is_active).length || 0
  const totalDiemUsage = keysUsage?.keys?.reduce((sum, k) => sum + k.diem_usage, 0) || 0
  const totalUsdUsage = keysUsage?.keys?.reduce((sum, k) => sum + k.usd_usage, 0) || 0

  const diemPerUsd = usage && usage.usd > 0 ? usage.diem / usage.usd : 0

  const getUsageTrend = () => {
    if (!keysUsage?.keys || keysUsage.keys.length === 0) return 'stable'
    const avgUsage = totalDiemUsage / keysUsage.keys.length
    const highUsageKeys = keysUsage.keys.filter(k => k.diem_usage > avgUsage * 1.5).length
    if (highUsageKeys > keysUsage.keys.length / 2) return 'increasing'
    if (highUsageKeys < keysUsage.keys.length / 4) return 'decreasing'
    return 'stable'
  }

  const trend = getUsageTrend()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Usage Analytics</h1>
        <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
          <Activity className="w-4 h-4" />
          {today}
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="flex items-center justify-center h-24">
                <div className="animate-pulse text-muted-foreground">Loading...</div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Epoch DIEM Spent
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(usage?.diem || 0, 4)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  This epoch
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Epoch USD Spent
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(usage?.usd || 0)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  This epoch
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Active API Keys
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{activeKeys} / {totalKeys}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {totalKeys - activeKeys} inactive
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Usage Trend
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  {trend === 'increasing' && (
                    <>
                      <TrendingUp className="w-5 h-5 text-yellow-500" />
                      <span className="text-lg font-semibold">Increasing</span>
                    </>
                  )}
                  {trend === 'decreasing' && (
                    <>
                      <TrendingDown className="w-5 h-5 text-emerald-500" />
                      <span className="text-lg font-semibold">Decreasing</span>
                    </>
                  )}
                  {trend === 'stable' && (
                    <>
                      <Minus className="w-5 h-5 text-blue-500" />
                      <span className="text-lg font-semibold">Stable</span>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                7-Day Usage Summary
              </CardTitle>
              <CardDescription>
                Aggregated usage across all API keys over the trailing 7-day period
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Total DIEM Consumed</p>
                  <p className="text-3xl font-bold">{formatNumber(totalDiemUsage, 4)}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Total USD Value</p>
                  <p className="text-3xl font-bold">{formatCurrency(totalUsdUsage)}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">DIEM Rate</p>
                  <p className="text-3xl font-bold">
                    {diemPerUsd > 0 ? formatNumber(diemPerUsd, 2) : '—'}
                    <span className="text-sm text-muted-foreground ml-1">/ USD</span>
                  </p>
                </div>
              </div>

              {usage?.epoch_start && (
                <div className="mt-6 pt-4 border-t border-border">
                  <p className="text-sm text-muted-foreground">
                    Epoch started: {formatDate(usage.epoch_start)}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {keysUsage?.keys && keysUsage.keys.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Key Usage Distribution</CardTitle>
                <CardDescription>
                  Per-key usage breakdown for the trailing 7-day period
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {keysUsage.keys
                    .sort((a, b) => b.diem_usage - a.diem_usage)
                    .slice(0, 5)
                    .map((key, index) => {
                      const percentage = totalDiemUsage > 0 
                        ? (key.diem_usage / totalDiemUsage) * 100 
                        : 0
                      return (
                        <div key={key.id} className="flex items-center gap-3">
                          <span className="text-sm font-medium w-6">{index + 1}.</span>
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium truncate max-w-[200px]">
                                {key.name}
                              </span>
                              <span className="text-sm text-muted-foreground">
                                {formatNumber(key.diem_usage, 4)} DIEM
                              </span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-primary rounded-full transition-all"
                                style={{ width: `${Math.min(percentage, 100)}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      )
                    })}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}