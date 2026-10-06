'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useAlertEvents, useAlerts, usePriceHistory } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useDisplayPreferences } from '@/components/PreferencesProvider'
import {
  alignSeries,
  computeEMA,
  computeRSI,
  computeSMA,
  matchAlertAnnotations,
  percentChange,
  sanitizeSeries,
  type SeriesPoint,
} from '@/lib/chart-analysis'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceDot,
} from 'recharts'

const RANGES = ['24h', '7d', '30d', '90d'] as const
const INDICATORS = [
  { value: 'none', label: 'No indicator' },
  { value: 'sma7', label: 'SMA 7' },
  { value: 'ema7', label: 'EMA 7' },
  { value: 'rsi14', label: 'RSI 14' },
] as const

type IndicatorValue = (typeof INDICATORS)[number]['value']
type RangeValue = (typeof RANGES)[number]

function formatTime(time: number, range: RangeValue, timezone: string) {
  return new Date(time).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: range === '24h' ? 'numeric' : undefined,
    ...(timezone === 'local' ? {} : { timeZone: timezone }),
  })
}

export function PriceChart() {
  const [token, setToken] = useState<'vvv' | 'diem'>('vvv')
  const [range, setRange] = useState<RangeValue>('7d')
  const [indicator, setIndicator] = useState<IndicatorValue>('none')
  const [compare, setCompare] = useState(false)
  const [showAnnotations, setShowAnnotations] = useState(true)
  const { timezone } = useDisplayPreferences()

  const { data, isLoading, isError } = usePriceHistory(token, range)
  const compareToken = token === 'vvv' ? 'diem' : 'vvv'
  const { data: compareData } = usePriceHistory(compareToken, range)
  const { data: alertsData } = useAlerts()
  const { data: eventsData } = useAlertEvents(false)

  const primarySeries: SeriesPoint[] = useMemo(
    () =>
      sanitizeSeries(
        (data?.data ?? []).map((point) => ({
          time: point.timestamp ? Date.parse(point.timestamp) : Number.NaN,
          value: point.price_usd,
        })),
      ),
    [data],
  )

  const secondarySeries: SeriesPoint[] = useMemo(
    () =>
      sanitizeSeries(
        (compareData?.data ?? []).map((point) => ({
          time: point.timestamp ? Date.parse(point.timestamp) : Number.NaN,
          value: point.price_usd,
        })),
      ),
    [compareData],
  )

  const indicatorSeries = useMemo(() => {
    if (indicator === 'sma7') return computeSMA(primarySeries, 7)
    if (indicator === 'ema7') return computeEMA(primarySeries, 7)
    if (indicator === 'rsi14') return computeRSI(primarySeries, 14)
    return []
  }, [indicator, primarySeries])

  const chartData = useMemo(() => {
    if (compare) {
      const aligned = alignSeries(primarySeries, secondarySeries)
      const basePrimary = primarySeries[0]?.value
      const baseSecondary = secondarySeries[0]?.value
      return aligned
        .filter((entry) => entry.left !== null || entry.right !== null)
        .map((entry) => ({
          time: entry.time,
          primary:
            entry.left !== null && basePrimary
              ? ((entry.left - basePrimary) / Math.abs(basePrimary)) * 100
              : null,
          secondary:
            entry.right !== null && baseSecondary
              ? ((entry.right - baseSecondary) / Math.abs(baseSecondary)) * 100
              : null,
        }))
    }
    return primarySeries.map((entry, index) => ({
      time: entry.time,
      usd: entry.value,
      indicator: indicatorSeries[index] ?? null,
    }))
  }, [compare, indicatorSeries, primarySeries, secondarySeries])

  const annotations = useMemo(() => {
    if (!data?.data?.length || !alertsData || !eventsData) return []
    const start = Date.parse(data.data[0].timestamp ?? '') || 0
    const end = Date.parse(data.data[data.data.length - 1].timestamp ?? '') || Date.now()
    return matchAlertAnnotations(
      eventsData.events,
      alertsData.alerts,
      `${token}_price_usd`,
      start,
      end,
    )
  }, [alertsData, data, eventsData, token])

  const primaryChange = percentChange(primarySeries)
  const secondaryChange = percentChange(secondarySeries)

  const showEmpty = !isLoading && !isError && chartData.length === 0

  return (
    <Card>
      <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <CardTitle>Price History</CardTitle>
          <CardDescription>
            Local snapshots from VeniceStats polls
            {data ? ` · ${data.count} point(s)` : ''}
            {primaryChange != null ? ` · ${primaryChange >= 0 ? '+' : ''}${primaryChange.toFixed(2)}%` : ''}
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
          <select
            value={indicator}
            onChange={(e) => setIndicator(e.target.value as IndicatorValue)}
            className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
            aria-label="Technical indicator"
          >
            {INDICATORS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <label className="inline-flex items-center gap-1.5 rounded-md border border-input px-3 py-1.5 text-sm">
            <input
              type="checkbox"
              checked={compare}
              onChange={(event) => setCompare(event.target.checked)}
              aria-label={`Compare with ${compareToken.toUpperCase()}`}
            />
            Compare {compareToken.toUpperCase()}
          </label>
          <label className="inline-flex items-center gap-1.5 rounded-md border border-input px-3 py-1.5 text-sm">
            <input
              type="checkbox"
              checked={showAnnotations}
              onChange={(event) => setShowAnnotations(event.target.checked)}
              aria-label="Show alert annotations"
            />
            Alerts
          </label>
          <button
            type="button"
            disabled
            title="Volume is unavailable: no authoritative public volume source was verified in Slice 2.0."
            className="rounded-md border border-dashed border-border px-3 py-1.5 text-sm text-muted-foreground"
          >
            Volume
          </button>
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
        <p className="mb-3 text-xs text-muted-foreground">
          Volume unavailable — no authoritative source was verified (Slice 2.0). Values are
          not synthesized.
        </p>
        {isLoading && (
          <div aria-live="polite" aria-busy="true" className="h-64 space-y-3 py-2">
            <span className="sr-only">Loading price history</span>
            <Skeleton aria-hidden="true" className="h-52 w-full" />
            <div className="flex justify-between">
              {[0, 1, 2, 3].map((tick) => (
                <Skeleton key={tick} aria-hidden="true" className="h-3 w-10" />
              ))}
            </div>
          </div>
        )}
        {isError && (
          <div className="h-64 flex items-center justify-center text-destructive text-sm">
            Failed to load price history
          </div>
        )}
        {showEmpty && (
          <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">
            No history yet — keep the app running to accumulate price snapshots.
          </div>
        )}
        {chartData.length > 0 && (
          <>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis
                    dataKey="time"
                    type="number"
                    domain={['dataMin', 'dataMax']}
                    tick={{ fontSize: 11 }}
                    tickFormatter={(value) => formatTime(Number(value), range, timezone)}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    domain={['auto', 'auto']}
                    tickFormatter={(value) => (compare ? `${Number(value).toFixed(1)}%` : String(value))}
                  />
                  <Tooltip
                    labelFormatter={(value) => formatTime(Number(value), range, timezone)}
                  />
                  {compare ? (
                    <>
                      <Line
                        type="monotone"
                        dataKey="primary"
                        name={`${token.toUpperCase()} % change`}
                        stroke="hsl(var(--chart-1))"
                        strokeWidth={2}
                        dot={false}
                        connectNulls
                      />
                      <Line
                        type="monotone"
                        dataKey="secondary"
                        name={`${compareToken.toUpperCase()} % change`}
                        stroke="hsl(var(--chart-3))"
                        strokeWidth={2}
                        dot={false}
                        connectNulls
                      />
                    </>
                  ) : (
                    <>
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
                        dataKey="indicator"
                        name={INDICATORS.find((option) => option.value === indicator)?.label ?? 'Indicator'}
                        stroke="hsl(var(--chart-4, 280 65% 60%))"
                        strokeWidth={1.5}
                        dot={false}
                        connectNulls
                        hide={indicator === 'none'}
                      />
                    </>
                  )}
                  {showAnnotations &&
                    !compare &&
                    annotations.map((annotation) => (
                      <ReferenceDot
                        key={annotation.id}
                        x={annotation.triggeredAt}
                        y={annotation.value}
                        r={5}
                        fill="hsl(var(--destructive))"
                        stroke="hsl(var(--background))"
                        strokeWidth={2}
                      />
                    ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            {showAnnotations && annotations.length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-2" aria-label="Alert annotations">
                {annotations.map((annotation) => (
                  <li key={annotation.id}>
                    <Link
                      href={`/alerts#event-${annotation.id}`}
                      className="inline-flex items-center gap-1 rounded-full border border-destructive/40 bg-destructive/10 px-3 py-1 text-xs text-destructive hover:underline"
                    >
                      {annotation.message}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {compare && (
              <p className="mt-3 text-xs text-muted-foreground">
                Comparison normalizes both series to percent change over the same {range} window
                (secondary: {secondaryChange != null ? `${secondaryChange.toFixed(2)}%` : '—'}).
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
