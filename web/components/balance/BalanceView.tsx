'use client'

import { useBalance, useDailyUsage } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatNumber, formatCurrency, cn } from '@/lib/utils'
import { Wallet, Clock, TrendingUp } from 'lucide-react'

export function BalanceView() {
  const { data: balance, isLoading: balanceLoading } = useBalance()
  const { data: usage, isLoading: usageLoading } = useDailyUsage()

  if (balanceLoading || usageLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-foreground">Balance & Limits</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="w-5 h-5" />
              Current Balance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
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
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Today&apos;s Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">DIEM Consumed</p>
              <p className="text-4xl font-bold text-foreground">
                {usage ? formatNumber(usage.diem, 4) : '—'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">USD Consumed</p>
              <p className="text-4xl font-bold text-foreground">
                {usage ? formatCurrency(usage.usd) : '—'}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {balance?.next_epoch_begins && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Epoch Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Next Epoch Begins</p>
                <p className="text-xl font-semibold text-foreground">
                  {new Date(balance.next_epoch_begins).toLocaleString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}