'use client'

import { useBalance } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency, formatNumber, cn } from '@/lib/utils'
import { Wallet, TrendingUp, TrendingDown, Clock } from 'lucide-react'

export function HeroBalanceCard() {
  const { data: balance, isLoading, isError } = useBalance()

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-48">
          <div className="animate-pulse text-muted-foreground">Loading balance...</div>
        </CardContent>
      </Card>
    )
  }

  if (isError || !balance) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-48">
          <div className="text-destructive">Failed to load balance</div>
        </CardContent>
      </Card>
    )
  }

  const diemUsagePercent = balance.diem_usage_percent
  const usdUsagePercent = balance.usd_usage_percent

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-xl">
          <Wallet className="w-5 h-5" />
          Account Balance
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">DIEM Balance</p>
              <p className="text-4xl font-bold text-foreground">
                {formatNumber(balance.diem, 2)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Daily Limit</p>
              <p className="text-lg font-medium text-foreground">
                {formatNumber(balance.daily_diem_limit, 2)}
              </p>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-muted-foreground">Usage</span>
                <span className={cn(
                  "font-medium",
                  diemUsagePercent > 80 ? "text-destructive" : "text-foreground"
                )}>
                  {diemUsagePercent.toFixed(1)}%
                </span>
              </div>
              <div className="h-2 bg-secondary rounded-full overflow-hidden">
                <div 
                  className={cn(
                    "h-full rounded-full transition-all",
                    diemUsagePercent > 80 ? "bg-destructive" : "bg-primary"
                  )}
                  style={{ width: `${Math.min(diemUsagePercent, 100)}%` }}
                />
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">USD Balance</p>
              <p className="text-4xl font-bold text-foreground">
                {formatCurrency(balance.usd)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Daily Limit</p>
              <p className="text-lg font-medium text-foreground">
                {formatCurrency(balance.daily_usd_limit)}
              </p>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-muted-foreground">Usage</span>
                <span className={cn(
                  "font-medium",
                  usdUsagePercent > 80 ? "text-destructive" : "text-foreground"
                )}>
                  {usdUsagePercent.toFixed(1)}%
                </span>
              </div>
              <div className="h-2 bg-secondary rounded-full overflow-hidden">
                <div 
                  className={cn(
                    "h-full rounded-full transition-all",
                    usdUsagePercent > 80 ? "bg-destructive" : "bg-primary"
                  )}
                  style={{ width: `${Math.min(usdUsagePercent, 100)}%` }}
                />
              </div>
            </div>
          </div>
        </div>
        
        {balance.next_epoch_begins && (
          <div className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span>Epoch resets: {new Date(balance.next_epoch_begins).toLocaleString()}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}