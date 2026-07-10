'use client'

import { useState } from 'react'
import { useAnalytics, useDailyAnalytics } from '@/hooks/useAnalytics'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from 'recharts'
import { Activity, DollarSign, Clock, Zap, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'
import { cn, getPriorityStyles } from '@/lib/utils'

const CHART_COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
  'hsl(330 80% 60%)',
  'hsl(188 78% 45%)',
  'hsl(82 85% 45%)',
  'hsl(24 95% 55%)',
  'hsl(240 75% 65%)',
]

const TYPE_ICONS = {
  efficiency: Zap,
  performance: Clock,
  cost: DollarSign,
}

interface ModelAnalyticsProps {
  className?: string
}

export function ModelAnalytics({ className }: ModelAnalyticsProps) {
  const [days, setDays] = useState(7)
  const [modelType, setModelType] = useState<string>('all')
  const { data: analytics, isLoading: analyticsLoading, error: analyticsError } = useAnalytics(days)
  const { data: dailyData, isLoading: dailyLoading } = useDailyAnalytics(days)

  if (analyticsLoading || dailyLoading) {
    return (
      <div className={cn("space-y-6", className)}>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Model Analytics</h2>
          <div className="animate-pulse h-8 w-32 bg-muted rounded" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="py-6">
                <div className="animate-pulse h-16 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (analyticsError || !analytics) {
    return (
      <Card className={className}>
        <CardContent className="py-12">
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <AlertCircle className="w-8 h-8" />
            <p>Failed to load analytics data</p>
            <p className="text-sm">Make sure the backend is running and you have usage history</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const { model_usage, total_requests, total_tokens, total_cost, recommendations } = analytics

  // Derive available model types for the filter dropdown
  const availableTypes = Array.from(
    new Set(Object.values(model_usage).map((d) => d.model_type || 'other'))
  ).sort()

  // Filter model_usage by selected model type
  const filteredUsage = modelType === 'all'
    ? model_usage
    : Object.fromEntries(
        Object.entries(model_usage).filter(([, d]) => (d.model_type || 'other') === modelType)
      )

  const filteredTotalRequests = Object.values(filteredUsage).reduce((s, d) => s + d.requests, 0)
  const filteredTotalTokens = Object.values(filteredUsage).reduce((s, d) => s + d.tokens, 0)
  const filteredTotalCost = Object.values(filteredUsage).reduce((s, d) => s + d.cost, 0)

  const modelData = Object.entries(filteredUsage)
    .map(([name, data]) => ({
      name: name.length > 30 ? name.substring(0, 30) + '...' : name,
      fullName: name,
      requests: data.requests,
      tokens: data.tokens,
      cost: data.cost,
      avgResponseTime: data.avg_response_time_ms,
    }))
    .sort((a, b) => b.cost - a.cost)
    .slice(0, 10)

  const costBreakdown = modelData.slice(0, 8).map((m, i) => ({
    ...m,
    color: CHART_COLORS[i % CHART_COLORS.length],
  }))

  const dailyChartData = dailyData?.daily_usage.map((d) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    requests: d.requests,
    tokens: d.tokens / 1000,
    cost: d.cost,
  })) || []

  const formatNumber = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
    return n.toFixed(0)
  }

  const formatCost = (n: number) => {
    if (n >= 1000) return `${(n / 1000).toFixed(2)}K`
    return n.toFixed(4)
  }

  return (
    <div className={cn("space-y-6", className)}>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Model Analytics</h2>
        <div className="flex items-center gap-2">
          <select
            value={modelType}
            onChange={(e) => setModelType(e.target.value)}
            className="px-3 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="all">All types</option>
            {availableTypes.map((t) => (
              <option key={t} value={t}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-3 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value={1}>Last 1 day</option>
            <option value={3}>Last 3 days</option>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Activity className="w-4 h-4" />
              <span className="text-sm">Total Requests</span>
            </div>
            <p className="text-2xl font-bold mt-1">{formatNumber(filteredTotalRequests)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <TrendingUp className="w-4 h-4" />
              <span className="text-sm">Total Tokens</span>
            </div>
            <p className="text-2xl font-bold mt-1">{formatNumber(filteredTotalTokens)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <DollarSign className="w-4 h-4" />
              <span className="text-sm">Total Cost</span>
            </div>
            <p className="text-2xl font-bold mt-1">{formatCost(filteredTotalCost)} DIEM</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Zap className="w-4 h-4" />
              <span className="text-sm">Models Used</span>
            </div>
            <p className="text-2xl font-bold mt-1">{Object.keys(filteredUsage).length}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Usage by Model</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={modelData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis type="number" className="text-xs" tickFormatter={formatNumber} />
                  <YAxis type="category" dataKey="name" className="text-xs" width={100} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                    formatter={(value: number, name: string) => [
                      name === 'tokens' ? formatNumber(value) : value,
                      name,
                    ]}
                  />
                  <Bar dataKey="tokens" fill="hsl(var(--chart-1))" name="Tokens" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Cost Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={costBreakdown}
                    dataKey="cost"
                    nameKey="name"
                    cx="70%"
                    cy="50%"
                    outerRadius={110}
                  >
                    {costBreakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || !payload.length) return null
                      const entry = payload[0]
                      return (
                        <div style={{
                          backgroundColor: 'hsl(var(--background))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '6px',
                          padding: '8px 12px',
                        }}>
                          <p className="text-sm font-medium">{entry.name}</p>
                          <p className="text-sm text-muted-foreground">{formatCost(entry.value as number)} DIEM</p>
                        </div>
                      )
                    }}
                  />
                  <Legend
                    layout="vertical"
                    verticalAlign="middle"
                    align="left"
                    iconType="circle"
                    iconSize={8}
                    formatter={(value: string) => (
                      <span className="text-xs text-muted-foreground">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Daily Usage Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyChartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" className="text-xs" />
                <YAxis yAxisId="left" className="text-xs" tickFormatter={formatNumber} />
                <YAxis yAxisId="right" orientation="right" className="text-xs" tickFormatter={(v) => `${v.toFixed(2)}`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--background))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px',
                  }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="tokens"
                  stroke="hsl(var(--chart-1))"
                  name="Tokens (K)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="cost"
                  stroke="hsl(var(--chart-2))"
                  name="Cost (DIEM)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Performance Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-3 font-medium">Model</th>
                  <th className="text-right py-2 px-3 font-medium">Requests</th>
                  <th className="text-right py-2 px-3 font-medium">Tokens</th>
                  <th className="text-right py-2 px-3 font-medium">Cost</th>
                  <th className="text-right py-2 px-3 font-medium">Avg Latency</th>
                </tr>
              </thead>
              <tbody>
                {modelData.map((model, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-muted/30">
                    <td className="py-2 px-3 font-medium" title={model.fullName}>
                      {model.name}
                    </td>
                    <td className="text-right py-2 px-3">{formatNumber(model.requests)}</td>
                    <td className="text-right py-2 px-3">{formatNumber(model.tokens)}</td>
                    <td className="text-right py-2 px-3">{formatCost(model.cost)}</td>
                    <td className="text-right py-2 px-3">
                      {model.avgResponseTime > 0
                        ? `${(model.avgResponseTime / 1000).toFixed(2)}s`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {recommendations.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recommendations.map((rec, i) => {
                const Icon = TYPE_ICONS[rec.type as keyof typeof TYPE_ICONS] || AlertCircle
                return (
                  <div
                    key={i}
                    className={cn(
                      "flex items-start gap-3 p-3 rounded-lg border",
                      getPriorityStyles(rec.priority as 'high' | 'medium' | 'low')
                    )}
                  >
                    <Icon className="w-5 h-5 mt-0.5 shrink-0" />
                    <div>
                      <p className="font-medium">{rec.type.charAt(0).toUpperCase() + rec.type.slice(1)}</p>
                      <p className="text-sm opacity-80">{rec.message}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}