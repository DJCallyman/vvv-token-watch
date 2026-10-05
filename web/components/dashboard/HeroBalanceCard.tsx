'use client'

import { useBalance } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency, formatDateTime, formatNumber } from '@/lib/utils'
import { Wallet, Clock } from 'lucide-react'
import { useDisplayPreferences } from '@/components/PreferencesProvider'

export function HeroBalanceCard() {
  const { data: balance, isLoading, isError } = useBalance()
  const { timezone } = useDisplayPreferences()

  if (isLoading) {
    return (
      <Card aria-busy="true" aria-live="polite" className="h-full">
        <span className="sr-only">Loading balance</span>
        <CardHeader className="pb-2 space-y-2">
          <Skeleton aria-hidden="true" className="h-6 w-40" />
          <Skeleton aria-hidden="true" className="h-3 w-48" />
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-6">
            <Skeleton aria-hidden="true" className="h-14 w-full" />
            <Skeleton aria-hidden="true" className="h-14 w-full" />
          </div>
          <Skeleton aria-hidden="true" className="h-4 w-52" />
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

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-xl">
          <Wallet className="w-5 h-5" />
          Account Balance
        </CardTitle>
        <p className="text-xs text-muted-foreground">Remaining credit in current epoch</p>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">DIEM</p>
            <p className="text-4xl font-bold text-foreground">
              {formatNumber(balance.diem, 4)}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">USD</p>
            <p className="text-4xl font-bold text-foreground">
              {formatCurrency(balance.usd)}
            </p>
          </div>
        </div>

        {balance.next_epoch_begins && (
          <div className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span>Epoch resets: {formatDateTime(balance.next_epoch_begins, timezone)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}