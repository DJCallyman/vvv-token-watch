'use client'

import { useBalance, useEpochUsage } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { formatNumber, formatCurrency, formatDateTime } from '@/lib/utils'
import { Wallet, TrendingUp, Clock, PieChart, Activity, AlertCircle } from 'lucide-react'

export function BalanceView() {
  const { data: balance, isLoading: balanceLoading, isError: balanceError } = useBalance()
  const { data: epochUsage, isLoading: epochLoading, isError: epochError } = useEpochUsage()

  const isLoading = balanceLoading || epochLoading
  const isError = balanceError || epochError

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    )
  }

  if (isError && !balance && !epochUsage) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Failed to load balance data</div>
      </div>
    )
  }

  const epochStart = epochUsage?.epoch_start ? new Date(epochUsage.epoch_start) : null
  const nextEpoch = balance?.next_epoch_begins ? new Date(balance.next_epoch_begins) : null
  
  let epochProgress = 0
  if (epochStart && nextEpoch) {
    const totalEpoch = nextEpoch.getTime() - epochStart.getTime()
    const elapsed = Date.now() - epochStart.getTime()
    epochProgress = Math.min(100, Math.max(0, (elapsed / totalEpoch) * 100))
  }

  const remainingDiem = balance?.diem || 0
  const consumedDiem = epochUsage?.diem || 0
  const totalDiemLimit = remainingDiem + consumedDiem
  const consumptionRate = totalDiemLimit > 0 ? (consumedDiem / totalDiemLimit) * 100 : 0

  const diemPerUsd = epochUsage && epochUsage.usd > 0 ? epochUsage.diem / epochUsage.usd : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Balance & Limits</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Account balance, usage limits, and epoch information
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="w-5 h-5" />
              Remaining Balance
            </CardTitle>
            <CardDescription>Your current credit balance</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <p className="text-sm text-muted-foreground">DIEM Balance</p>
              <p className="text-4xl font-bold text-foreground">
                {balance ? formatNumber(balance.diem, 4) : '—'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">USD Balance</p>
              <p className="text-4xl font-bold text-foreground">
                {balance ? formatCurrency(balance.usd) : '—'}
              </p>
            </div>
            <div className="pt-4 border-t border-border">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Consumption</span>
                <span className="font-medium">{consumptionRate.toFixed(1)}% used</span>
              </div>
              <div className="mt-2 h-3 bg-muted rounded-full overflow-hidden">
                <div 
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${Math.min(consumptionRate, 100)}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Epoch Consumption
            </CardTitle>
            <CardDescription>Usage since epoch started</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <p className="text-sm text-muted-foreground">DIEM Consumed</p>
              <p className="text-4xl font-bold text-foreground">
                {epochUsage ? formatNumber(epochUsage.diem, 4) : '—'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">USD Consumed</p>
              <p className="text-4xl font-bold text-foreground">
                {epochUsage ? formatCurrency(epochUsage.usd) : '—'}
              </p>
            </div>
            {diemPerUsd > 0 && (
              <div className="pt-4 border-t border-border">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Exchange Rate</span>
                  <span className="text-lg font-semibold">
                    {formatNumber(diemPerUsd, 2)} DIEM / USD
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {balance?.daily_diem_limit !== undefined && balance.daily_usd_limit !== undefined && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Daily Rate Limits
            </CardTitle>
            <CardDescription>Per-day consumption caps</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">DIEM Daily Limit</p>
                <p className="text-2xl font-bold">{formatNumber(balance.daily_diem_limit, 4)}</p>
              </div>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">USD Daily Limit</p>
                <p className="text-2xl font-bold">{formatCurrency(balance.daily_usd_limit)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      {nextEpoch && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Epoch Information
            </CardTitle>
            <CardDescription>Billing cycle details</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Epoch Started</p>
                  <p className="text-lg font-semibold">
                    {epochStart ? formatDateTime(epochStart.toISOString()) : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Next Epoch Begins</p>
                  <p className="text-lg font-semibold">
                    {formatDateTime(balance?.next_epoch_begins ?? '')}
                  </p>
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Epoch Progress</p>
                  <div className="h-4 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${Math.min(epochProgress, 100)}%` }}
                    />
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {epochProgress.toFixed(1)}% complete
                  </p>
                </div>
                {(balance?.diem_consumed_percent !== undefined || balance?.usd_consumed_percent !== undefined) && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <AlertCircle className="w-4 h-4 text-yellow-500" />
                      <p className="text-sm text-muted-foreground">Usage (Consumed % of limit/allocation)</p>
                    </div>
                    <p className="text-lg font-semibold">
                      DIEM: {balance.diem_consumed_percent != null ? balance.diem_consumed_percent.toFixed(1) + '%' : '—'} | USD: {balance.usd_consumed_percent != null ? balance.usd_consumed_percent.toFixed(1) + '%' : '—'}
                    </p>
                    <p className="text-[10px] text-muted-foreground mt-1">Same rule (e.g. gte 80) now means the same thing for both currencies.</p>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="w-5 h-5" />
            Balance Summary
          </CardTitle>
          <CardDescription>Quick overview of all balance metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Remaining DIEM</p>
              <p className="text-xl font-bold">{formatNumber(remainingDiem, 4)}</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Remaining USD</p>
              <p className="text-xl font-bold">{formatCurrency(balance?.usd || 0)}</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Consumed DIEM</p>
              <p className="text-xl font-bold">{formatNumber(consumedDiem, 4)}</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Consumed USD</p>
              <p className="text-xl font-bold">{formatCurrency(epochUsage?.usd || 0)}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}