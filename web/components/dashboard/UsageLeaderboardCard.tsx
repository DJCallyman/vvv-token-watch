'use client'

import { useState, useMemo } from 'react'
import { useAPIKeysUsage } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatNumber, formatCurrency, cn, getUsagePercentile, getUsageBarColor } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { BarChart3, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

type SortMode = 'usage_high' | 'usage_low' | 'name_asc' | 'name_desc' | 'recent'

export function UsageLeaderboardCard() {
  const { data: usage, isLoading, isError } = useAPIKeysUsage()
  const [sortMode, setSortMode] = useState<SortMode>('usage_high')

  const sortedKeys = useMemo(() => {
    if (!usage?.keys) return []
    
    const keys = [...usage.keys]
    
    switch (sortMode) {
      case 'usage_high':
        return keys.sort((a, b) => b.diem_usage - a.diem_usage)
      case 'usage_low':
        return keys.sort((a, b) => a.diem_usage - b.diem_usage)
      case 'name_asc':
        return keys.sort((a, b) => a.name.localeCompare(b.name))
      case 'name_desc':
        return keys.sort((a, b) => b.name.localeCompare(a.name))
      case 'recent':
        return keys.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      default:
        return keys
    }
  }, [usage?.keys, sortMode])

  const maxUsage = useMemo(() => {
    if (!usage?.keys || usage.keys.length === 0) return 0
    return Math.max(...usage.keys.map(k => k.diem_usage))
  }, [usage?.keys])

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-48">
          <div className="animate-pulse text-muted-foreground">Loading usage data...</div>
        </CardContent>
      </Card>
    )
  }

  if (isError || !usage) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-48">
          <div className="text-destructive">Failed to load usage data</div>
        </CardContent>
      </Card>
    )
  }

  const totalUsage = usage.keys.reduce((sum, k) => sum + k.diem_usage, 0)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            API Key Usage (7-Day Trailing)
          </CardTitle>
          <div className="flex items-center gap-1">
            <span className="text-sm text-muted-foreground mr-2">
              Total: {formatNumber(totalUsage, 4)} DIEM
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <span className="text-xs text-muted-foreground">Sort by:</span>
          <div className="flex gap-1">
            <SortButton 
              label="Usage" 
              active={sortMode === 'usage_high' || sortMode === 'usage_low'} 
              onClick={() => setSortMode(sortMode === 'usage_high' ? 'usage_low' : 'usage_high')}
            />
            <SortButton 
              label="Name" 
              active={sortMode === 'name_asc' || sortMode === 'name_desc'} 
              onClick={() => setSortMode(sortMode === 'name_asc' ? 'name_desc' : 'name_asc')}
            />
            <SortButton 
              label="Recent" 
              active={sortMode === 'recent'} 
              onClick={() => setSortMode('recent')}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {sortedKeys.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">No API keys found</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-1/3">DIEM Usage</TableHead>
                <TableHead className="text-right">USD Usage</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedKeys.map((key) => {
                const percentile = getUsagePercentile(key.diem_usage, maxUsage)
                const barColor = getUsageBarColor(percentile)
                
                return (
                  <TableRow key={key.id}>
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell>
                      <Badge variant={key.is_active ? "success" : "secondary"}>
                        {key.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-mono">{formatNumber(key.diem_usage, 4)}</span>
                          <span className="text-xs text-muted-foreground">
                            {percentile.toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div 
                            className={cn("h-full rounded-full transition-all", barColor)}
                            style={{ width: `${Math.min(percentile, 100)}%` }}
                          />
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(key.usd_usage)}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

function SortButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-2 py-1 text-xs rounded transition-colors",
        active 
          ? "bg-primary text-primary-foreground" 
          : "bg-muted hover:bg-muted/80 text-muted-foreground"
      )}
    >
      {label}
    </button>
  )
}