'use client'

import { useBalance } from '@/lib/hooks'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { Activity, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export function Header() {
  const { data: balance, isLoading, isError } = useBalance()

  return (
    <header className="h-16 border-b border-border bg-card px-6 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Badge
          variant={isError ? 'destructive' : isLoading ? 'secondary' : 'success'}
          className="gap-1"
        >
          <Activity className="w-3 h-3" />
          {isError ? 'Disconnected' : isLoading ? 'Connecting' : 'Connected'}
        </Badge>
      </div>
      
      <div className="flex items-center gap-6">
        {balance && (
          <>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">DIEM Balance</p>
              <p className="font-semibold text-foreground">
                {formatNumber(balance.diem, 2)}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">USD Balance</p>
              <p className="font-semibold text-foreground">
                {formatCurrency(balance.usd)}
              </p>
            </div>
          </>
        )}
        
        <div className="flex items-center gap-2">
          {isLoading && (
            <RefreshCw className="w-4 h-4 animate-spin text-muted-foreground" />
          )}
        </div>
      </div>
    </header>
  )
}