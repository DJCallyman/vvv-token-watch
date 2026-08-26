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
import { cn, formatCurrency, formatNumber as formatFixedNumber, getPriorityStyles } from '@/lib/utils'

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

const BREAKDOWN_LABELS: Record<string, string> = {
  input: 'Input',
  output: 'Output',
  'cache-input': 'Cache read',
  'cache-write': 'Cache write',
}

interface ModelAnalyticsProps {
  className?: string
}

export function ModelAnalytics({ className }: ModelAnalyticsProps) {
  const [days, setDays] = useState(7)
  const [modelType, setModelType] = useState<string>('all')
  const { data: analytics, isLoading: analyticsLoading, error: analyticsError } = useAnalytics(days)
  const { data: dailyData, isLoading: dailyLoading, error: dailyError } = useDailyAnalytics(days)

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

  const { model_usage, total_requests, total_tokens, total_cost, recommendations, source } = analytics
  const isBillingAnalytics = source === 'billing/usage-analytics'

  // BUG-08: when using the lighter analytics endpoint, requests and latency are not provided
  const showRequestLatency = !isBillingAnalytics

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

  const filteredTotalRequests = Object.values(filteredUsage).reduce((s, d) => s + (d.requests ?? 0), 0)
  const filteredTotalTokens = Object.values(filteredUsage).reduce((s, d) => s + d.tokens, 0)
  const filteredTotalUsd = Object.values(filteredUsage).reduce((s, d) => s + (d.cost_usd ?? 0), 0)
  const filteredTotalDiem = Object.values(filteredUsage).reduce((s, d) => s + (d.cost_diem ?? 0), 0)
  const filteredTotalBundledCredits = Object.values(filteredUsage).reduce((s, d) => s + (d.cost_bundled_credits ?? 0), 0)

  const modelData = Object.entries(filteredUsage)
    .map(([name, data]) => ({
      name: name.length > 30 ? name.substring(0, 30) + '...' : name,
      fullName: name,
      requests: data.requests,
      tokens: data.tokens,
      cost: data.cost,
      costUsd: data.cost_usd ?? 0,
      costDiem: data.cost_diem ?? 0,
      costBundledCredits: data.cost_bundled_credits ?? 0,
      avgResponseTime: data.avg_response_time_ms,
      breakdown: data.breakdown ?? [],
    }))
    .sort((a, b) => b.cost - a.cost)
    .slice(0, 10)

  const costBreakdown = modelData.slice(0, 8).map((m, i) => ({
    ...m,
    color: CHART_COLORS[i % CHART_COLORS.length],
  }))
  const chartCurrency = filteredTotalUsd > 0 ? 'USD' : 'DIEM'
  const chartCostKey = filteredTotalUsd > 0 ? 'costUsd' : 'costDiem'
  const hasBreakdowns = modelData.some((model) => model.breakdown.length > 0)
  const dailyTotalUsd = dailyData?.daily_usage.reduce((sum, day) => sum + (day.cost_usd ?? 0), 0) ?? 0
  const dailyChartCurrency = dailyTotalUsd > 0 ? 'USD' : 'DIEM'
  const dailyHasTokens = dailyData?.daily_usage.some((day) => day.tokens != null) ?? false

  const dailyChartData = dailyData?.daily_usage.map((d) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    tokens: d.tokens == null ? undefined : d.tokens / 1000,
    cost: dailyChartCurrency === 'USD' ? d.cost_usd ?? 0 : d.cost_diem ?? 0,
  })) || []

  const formatCompactNumber = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
    return n.toFixed(0)
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
            <p className="text-2xl font-bold mt-1">
              {isBillingAnalytics ? '—' : formatCompactNumber(filteredTotalRequests)}
            </p>
            {isBillingAnalytics && (
              <p className="text-[10px] text-muted-foreground">Unavailable from this source</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <TrendingUp className="w-4 h-4" />
              <span className="text-sm">Total Tokens</span>
            </div>
            <p className="text-2xl font-bold mt-1">{formatCompactNumber(filteredTotalTokens)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <DollarSign className="w-4 h-4" />
              <span className="text-sm">Cost Summary</span>
            </div>
            <div className="mt-1 space-y-0.5">
              <p className="text-2xl font-bold">{formatCurrency(filteredTotalUsd)}</p>
              <p className="text-sm font-semibold">{formatFixedNumber(filteredTotalDiem, 4)} DIEM</p>
              {filteredTotalBundledCredits > 0 && (
                <p className="text-xs font-medium">{formatFixedNumber(filteredTotalBundledCredits, 4)} bundled credits</p>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground">Currencies kept separate</p>
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
                  <XAxis type="number" className="text-xs" tickFormatter={formatCompactNumber} />
                  <YAxis type="category" dataKey="name" className="text-xs" width={100} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                    formatter={(value: number, name: string) => [
                      name === 'tokens' ? formatCompactNumber(value) : value,
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
            <CardTitle className="text-base">Cost Distribution ({chartCurrency})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={costBreakdown}
                    dataKey={chartCostKey}
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
                          <p className="text-sm text-muted-foreground">
                            {chartCurrency === 'USD'
                              ? formatCurrency(entry.value as number)
                              : `${formatFixedNumber(entry.value as number, 4)} DIEM`}
                          </p>
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
          {dailyError ? (
            <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
              Daily trend data is unavailable.
            </div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dailyChartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="date" className="text-xs" />
                  <YAxis yAxisId="left" className="text-xs" tickFormatter={formatCompactNumber} />
                  <YAxis yAxisId="right" orientation="right" className="text-xs" tickFormatter={(v) => `${v.toFixed(2)}`} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                  />
                  <Legend />
                  {dailyHasTokens && (
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="tokens"
                      stroke="hsl(var(--chart-1))"
                      name="Tokens (K)"
                      strokeWidth={2}
                      dot={false}
                    />
                  )}
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="cost"
                    stroke="hsl(var(--chart-2))"
                    name={`Cost (${dailyChartCurrency})`}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
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
                  {!isBillingAnalytics && <th className="text-right py-2 px-3 font-medium">Requests</th>}
                  <th className="text-right py-2 px-3 font-medium">Tokens</th>
                  <th className="text-right py-2 px-3 font-medium">Cost</th>
                  {hasBreakdowns && <th className="text-left py-2 px-3 font-medium">Cost Breakdown</th>}
                  {showRequestLatency && <th className="text-right py-2 px-3 font-medium">Avg Latency</th>}
                </tr>
              </thead>
              <tbody>
                {modelData.map((model, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-muted/30">
                    <td className="py-2 px-3 font-medium" title={model.fullName}>
                      {model.name}
                    </td>
                    {!isBillingAnalytics && (
                      <td className="text-right py-2 px-3">
                        {model.requests == null ? '—' : formatCompactNumber(model.requests)}
                      </td>
                    )}
                    <td className="text-right py-2 px-3">{formatCompactNumber(model.tokens)}</td>
                    <td className="text-right py-2 px-3">
                      <div className="space-y-0.5">
                        {model.costUsd > 0 && <div>{formatCurrency(model.costUsd)}</div>}
                        {model.costDiem > 0 && <div>{formatFixedNumber(model.costDiem, 4)} DIEM</div>}
                        {model.costBundledCredits > 0 && <div>{formatFixedNumber(model.costBundledCredits, 4)} bundled</div>}
                        {model.costUsd <= 0 && model.costDiem <= 0 && model.costBundledCredits <= 0 && <div>—</div>}
                      </div>
                    </td>
                    {hasBreakdowns && (
                      <td className="py-2 px-3 text-xs text-muted-foreground">
                        {model.breakdown.length > 0 ? (
                          <div className="space-y-1">
                            {model.breakdown.map((breakdown, breakdownIndex) => {
                              const amounts = [
                                breakdown.usd !== 0 ? formatCurrency(breakdown.usd) : null,
                                breakdown.diem !== 0 ? `${formatFixedNumber(breakdown.diem, 4)} DIEM` : null,
                                breakdown.units !== 0 ? `${formatCompactNumber(breakdown.units)} units` : null,
                              ].filter(Boolean)
                              return (
                                <div key={`${breakdown.type}-${breakdownIndex}`}>
                                  <span className="font-medium text-foreground">
                                    {BREAKDOWN_LABELS[breakdown.type.toLowerCase()] || breakdown.type}
                                  </span>
                                  {amounts.length > 0 ? `: ${amounts.join(' · ')}` : ''}
                                </div>
                              )
                            })}
                          </div>
                        ) : '—'}
                      </td>
                    )}
                    {showRequestLatency && (
                      <td className="text-right py-2 px-3">
                        {model.avgResponseTime != null && model.avgResponseTime > 0
                          ? `${(model.avgResponseTime / 1000).toFixed(2)}s`
                          : '—'}
                      </td>
                    )}
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