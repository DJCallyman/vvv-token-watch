'use client'

import { useAPIKeysUsage } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatNumber, formatCurrency, cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { BarChart3 } from 'lucide-react'

export function UsageLeaderboardCard() {
  const { data: usage, isLoading, isError } = useAPIKeysUsage()

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

  const sortedKeys = [...usage.keys].sort((a, b) => b.diem_usage - a.diem_usage)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          API Key Usage (7-Day Trailing)
        </CardTitle>
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
                <TableHead className="text-right">DIEM Usage</TableHead>
                <TableHead className="text-right">USD Usage</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedKeys.map((key) => (
                <TableRow key={key.id}>
                  <TableCell className="font-medium">{key.name}</TableCell>
                  <TableCell>
                    <Badge variant={key.is_active ? "success" : "secondary"}>
                      {key.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatNumber(key.diem_usage, 4)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatCurrency(key.usd_usage)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}