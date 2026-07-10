'use client'

import { useBalance, useUnacknowledgedAlertEvents } from '@/lib/hooks'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { Activity, Bell, Moon, RefreshCw, Sun } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/components/ThemeProvider'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import Link from 'next/link'

export function Header() {
  const { data: balance, isLoading, isError, dataUpdatedAt } = useBalance()
  const { data: alertEvents } = useUnacknowledgedAlertEvents()
  const { theme, toggleTheme } = useTheme()
  const queryClient = useQueryClient()
  const [refreshing, setRefreshing] = useState(false)

  const unacked = alertEvents?.count ?? 0
  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : null

  const onRefresh = async () => {
    setRefreshing(true)
    try {
      await queryClient.invalidateQueries()
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <header className="h-16 border-b border-border bg-card px-4 sm:px-6 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <Badge
          variant={isError ? 'destructive' : isLoading ? 'secondary' : 'success'}
          className="gap-1"
        >
          <Activity className="w-3 h-3" />
          {isError ? 'Disconnected' : isLoading ? 'Connecting' : 'Connected'}
        </Badge>
        {lastUpdated && (
          <span className="hidden sm:inline text-xs text-muted-foreground">
            Updated {lastUpdated}
          </span>
        )}
      </div>

      <div className="flex items-center gap-4 sm:gap-6">
        {balance && (
          <>
            <div className="text-right hidden md:block">
              <p className="text-xs text-muted-foreground">DIEM Balance</p>
              <p className="font-semibold text-foreground">
                {formatNumber(balance.diem, 2)}
              </p>
            </div>
            <div className="text-right hidden md:block">
              <p className="text-xs text-muted-foreground">USD Balance</p>
              <p className="font-semibold text-foreground">
                {formatCurrency(balance.usd)}
              </p>
            </div>
          </>
        )}

        <Link
          href="/alerts"
          className="relative rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          aria-label={unacked > 0 ? `${unacked} unacknowledged alerts` : 'Alerts'}
        >
          <Bell className="w-4 h-4" />
          {unacked > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-[1rem] h-4 px-1 rounded-full bg-destructive text-[10px] leading-4 text-destructive-foreground text-center">
              {unacked > 99 ? '99+' : unacked}
            </span>
          )}
        </Link>

        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing || isLoading}
          className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
          aria-label="Refresh all data"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing || isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </header>
  )
}
