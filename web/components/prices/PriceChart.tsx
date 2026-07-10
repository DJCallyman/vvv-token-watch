'use client'

import { useState } from 'react'
import { usePriceHistory } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const RANGES = ['24h', '7d', '30d', '90d'] as const

export function PriceChart() {
  const [token, setToken] = useState<'vvv' | 'diem'>('vvv')
  const [range, setRange] = useState<(typeof RANGES)[number]>('7d')
  const { data, isLoading, isError } = usePriceHistory(token, range)

  const chartData =
    data?.data.map((p) => ({
      time: p.timestamp
        ? new Date(p.timestamp).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: range === '24h' ? 'numeric' : undefined,
          })
        : '',
      usd: p.price_usd,
      aud: p.price_aud,
    })) ?? []

  return (
    <Card>
      <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <CardTitle>Price History</CardTitle>
          <CardDescription>
            Local snapshots from CoinGecko polls
            {data ? ` · ${data.count} point(s)` : ''}
          </CardDescription>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={token}
            onChange={(e) => setToken(e.target.value as 'vvv' | 'diem')}
            className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
            aria-label="Token"
          >
            <option value="vvv">VVV</option>
            <option value="diem">DIEM</option>
          </select>
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRange(r)}
              className={`rounded-md px-3 py-1.5 text-sm border ${
                range === r
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border text-muted-foreground hover:bg-accent'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="h-64 flex items-center justify-center animate-pulse text-muted-foreground">
            Loading history…
          </div>
        )}
        {isError && (
          <div className="h-64 flex items-center justify-center text-destructive text-sm">
            Failed to load price history
          </div>
        )}
        {!isLoading && !isError && chartData.length === 0 && (
          <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">
            No history yet — keep the app running to accumulate price snapshots.
          </div>
        )}
        {chartData.length > 0 && (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="usd"
                  name="USD"
                  stroke="hsl(var(--chart-1))"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="aud"
                  name="AUD"
                  stroke="hsl(var(--chart-3))"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
