'use client'

import { usePrices } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { Coins, Info, TrendingUp } from 'lucide-react'
import { useDisplayPreferences } from '@/components/PreferencesProvider'

export function PriceCards() {
  const { data: prices, isLoading, isError } = usePrices()
  const { currency } = useDisplayPreferences()

  if (isLoading) {
    return (
      <div aria-live="polite" aria-busy="true" className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <span className="sr-only">Loading prices</span>
        {[0, 1].map((card) => (
          <Card key={card}>
            <CardHeader className="pb-2">
              <Skeleton aria-hidden="true" className="h-5 w-28" />
            </CardHeader>
            <CardContent className="space-y-3">
              <Skeleton aria-hidden="true" className="h-8 w-32" />
              <Skeleton aria-hidden="true" className="h-4 w-20" />
              <Skeleton aria-hidden="true" className="h-3 w-24" />
            </CardContent>
          </Card>
        ))}
        <Card>
          <CardHeader className="pb-2">
            <Skeleton aria-hidden="true" className="h-4 w-36" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton aria-hidden="true" className="h-9 w-36" />
            <Skeleton aria-hidden="true" className="h-2 w-full" />
            {[0, 1, 2].map((row) => (
              <Skeleton key={row} aria-hidden="true" className="h-4 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isError || !prices) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-32">
          <div className="text-destructive">Failed to load prices</div>
        </CardContent>
      </Card>
    )
  }

  const portfolio = prices.portfolio
  const vvvCurrency = currency === 'AUD' && prices.vvv?.aud != null ? 'AUD' : 'USD'
  const diemCurrency = currency === 'AUD' && prices.diem?.aud != null ? 'AUD' : 'USD'
  const vvvPrice = vvvCurrency === 'AUD' ? prices.vvv?.aud : prices.vvv?.usd
  const diemPrice = diemCurrency === 'AUD' ? prices.diem?.aud : prices.diem?.usd
  const grossExposureUsd = portfolio?.gross_exposure_usd ?? portfolio?.total_usd ?? 0
  const netWorthUsd = portfolio?.net_worth_usd ?? portfolio?.total_usd ?? 0
  const diemUnlockOffsetUsd = portfolio?.diem_unlock_offset_usd ?? 0
  const exposureParts = portfolio
    ? [
        { label: 'VVV', value: portfolio.vvv_value_usd, color: 'bg-red-500' },
        { label: 'sVVV', value: portfolio.svvv_value_usd ?? 0, color: 'bg-blue-500' },
        { label: 'DIEM', value: portfolio.diem_value_usd, color: 'bg-green-500' },
        { label: 'Unclaimed Rewards', value: portfolio.unclaimed_rewards_value_usd ?? 0, color: 'bg-amber-500' },
      ]
    : []
  const formatExposureCurrency = (value: number) =>
    Math.abs(value) < 10_000
      ? formatCurrency(value)
      : new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          notation: 'compact',
          maximumFractionDigits: 2,
        }).format(value)

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Coins className="w-4 h-4" />
            VVV Price
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold text-foreground">
            {formatCurrency(vvvPrice || 0, vvvCurrency)}
          </p>
          {typeof prices.vvv?.change_24h === 'number' && (
            <p
              className={`text-sm font-medium ${
                prices.vvv.change_24h >= 0 ? 'text-emerald-500' : 'text-red-500'
              }`}
            >
              {prices.vvv.change_24h >= 0 ? '▲' : '▼'} {formatNumber(Math.abs(prices.vvv.change_24h), 2)}% (24h)
            </p>
          )}
          {prices.vvv?.aud && (
            <p className="text-sm text-muted-foreground">
              {formatCurrency(prices.vvv.aud, 'AUD')}
            </p>
          )}
          {typeof prices.vvv?.market_cap === 'number' && (
            <p className="text-xs text-muted-foreground">
              MCap {formatCurrency(prices.vvv.market_cap)}
            </p>
          )}
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Coins className="w-4 h-4" />
            DIEM Price
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold text-foreground">
            {formatCurrency(diemPrice || 0, diemCurrency)}
          </p>
          {typeof prices.diem?.change_24h === 'number' && (
            <p
              className={`text-sm font-medium ${
                prices.diem.change_24h >= 0 ? 'text-emerald-500' : 'text-red-500'
              }`}
            >
              {prices.diem.change_24h >= 0 ? '▲' : '▼'} {formatNumber(Math.abs(prices.diem.change_24h), 2)}% (24h)
            </p>
          )}
          {prices.diem?.aud && (
            <p className="text-sm text-muted-foreground">
              {formatCurrency(prices.diem.aud, 'AUD')}
            </p>
          )}
          {typeof prices.diem?.market_cap === 'number' && (
            <p className="text-xs text-muted-foreground">
              MCap {formatCurrency(prices.diem.market_cap)}
            </p>
          )}
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Protocol Exposure
          </CardTitle>
        </CardHeader>
        <CardContent>
          {portfolio ? (
            <div className="space-y-4">
              <p className="text-3xl font-bold text-amber-500">
                {formatExposureCurrency(grossExposureUsd)}
              </p>
              <div
                className="flex h-2 w-full overflow-hidden rounded-full bg-muted"
                aria-label="Gross exposure composition"
              >
                {exposureParts.map((part) => (
                  <span
                    key={part.label}
                    className={`h-full shrink-0 ${part.color}`}
                    style={{
                      width: grossExposureUsd > 0
                        ? `${(part.value / grossExposureUsd) * 100}%`
                        : '0%',
                      minWidth: part.value > 0 ? 3 : 0,
                    }}
                    title={`${part.label}: ${formatCurrency(part.value)}`}
                  />
                ))}
              </div>
              <div className="space-y-2">
                {exposureParts.map((part) => (
                  <div key={part.label} className="flex items-center justify-between gap-3 text-sm">
                    <span className="flex min-w-0 items-center gap-2 text-muted-foreground">
                      <span className={`h-3 w-3 shrink-0 rounded ${part.color}`} />
                      <span className="truncate">{part.label}</span>
                    </span>
                    <span className="shrink-0 font-semibold text-foreground">
                      {formatExposureCurrency(part.value)}
                    </span>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between border-t border-border pt-3">
                <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  Net worth
                  <button
                    type="button"
                    className="inline-flex text-muted-foreground hover:text-foreground"
                    aria-label="Net worth subtracts the DIEM unlock offset from gross exposure."
                    title={`Gross exposure minus ${formatCurrency(diemUnlockOffsetUsd)} DIEM unlock offset`}
                  >
                    <Info className="h-4 w-4" aria-hidden="true" />
                  </button>
                </span>
                <span className="text-xl font-semibold text-foreground">
                  {formatExposureCurrency(netWorthUsd)}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">Set holdings to view portfolio</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}