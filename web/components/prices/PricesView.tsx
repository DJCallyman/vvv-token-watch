'use client'

import { useState } from 'react'
import { usePrices } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { Coins, Wallet } from 'lucide-react'

type Currency = 'USD' | 'AUD'

export function PricesView() {
  const { data: prices, isLoading, isError } = usePrices()
  const [portfolioCurrency, setPortfolioCurrency] = useState<Currency>('USD')

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-muted-foreground">Loading prices...</div>
      </div>
    )
  }

  if (isError || !prices) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Failed to load prices</div>
      </div>
    )
  }

  const vvvPrice = prices.vvv?.usd || 0
  const diemPrice = prices.diem?.usd || 0
  const vvvAud = prices.vvv?.aud
  const diemAud = prices.diem?.aud

  const vvvHoldings = prices.holdings?.vvv || 0
  const diemHoldings = prices.holdings?.diem || 0

  const vvvValueUsd = prices.portfolio?.vvv_value_usd || (vvvPrice * vvvHoldings)
  const diemValueUsd = prices.portfolio?.diem_value_usd || (diemPrice * diemHoldings)

  const vvvValueAud = vvvAud != null ? vvvAud * vvvHoldings : null
  const diemValueAud = diemAud != null ? diemAud * diemHoldings : null

  const portfolioVvvValue = portfolioCurrency === 'AUD' ? vvvValueAud : vvvValueUsd
  const portfolioDiemValue = portfolioCurrency === 'AUD' ? diemValueAud : diemValueUsd
  const portfolioVvvPrice = portfolioCurrency === 'AUD' ? vvvAud : vvvPrice
  const portfolioDiemPrice = portfolioCurrency === 'AUD' ? diemAud : diemPrice

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Token Prices</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Live prices and portfolio values from CoinGecko
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Coins className="w-5 h-5" />
              VVV Token
            </CardTitle>
            <CardDescription>Venice Token</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Price (USD)</p>
                <p className="text-3xl font-bold text-foreground">
                  {formatCurrency(vvvPrice)}
                </p>
              </div>
              {vvvAud != null && (
                <div>
                  <p className="text-sm text-muted-foreground">Price (AUD)</p>
                  <p className="text-3xl font-bold text-foreground">
                    {formatCurrency(vvvAud, 'AUD')}
                  </p>
                </div>
              )}
            </div>
            <div className="pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground mb-1">Your Holdings</p>
              <p className="text-xl font-semibold text-foreground">
                {formatNumber(vvvHoldings)} VVV
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                ≈ {formatCurrency(vvvValueUsd)}
              </p>
              {vvvValueAud != null && (
                <p className="text-sm text-muted-foreground mt-0.5">
                  ≈ {formatCurrency(vvvValueAud, 'AUD')}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Coins className="w-5 h-5" />
              DIEM Token
            </CardTitle>
            <CardDescription>Venice Credit Token</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Price (USD)</p>
                <p className="text-3xl font-bold text-foreground">
                  {formatCurrency(diemPrice)}
                </p>
              </div>
              {diemAud != null && (
                <div>
                  <p className="text-sm text-muted-foreground">Price (AUD)</p>
                  <p className="text-3xl font-bold text-foreground">
                    {formatCurrency(diemAud, 'AUD')}
                  </p>
                </div>
              )}
            </div>
            <div className="pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground mb-1">Your Holdings</p>
              <p className="text-xl font-semibold text-foreground">
                {formatNumber(diemHoldings)} DIEM
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                ≈ {formatCurrency(diemValueUsd)}
              </p>
              {diemValueAud != null && (
                <p className="text-sm text-muted-foreground mt-0.5">
                  ≈ {formatCurrency(diemValueAud, 'AUD')}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
      
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Wallet className="w-5 h-5" />
                Portfolio Summary
              </CardTitle>
              <CardDescription>Your combined token holdings</CardDescription>
            </div>
            <label htmlFor="portfolio-currency" className="sr-only">Portfolio currency</label>
            <select
              id="portfolio-currency"
              value={portfolioCurrency}
              onChange={(e) => setPortfolioCurrency(e.target.value as Currency)}
              className="text-sm rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="USD">USD</option>
              <option value="AUD">AUD</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-lg bg-muted/50 p-4">
              <div className="flex items-center gap-2 mb-2">
                <Coins className="w-4 h-4 text-primary" />
                <p className="text-xs text-muted-foreground uppercase tracking-wide">VVV Value</p>
              </div>
              <p className="text-2xl font-bold">
                {portfolioVvvValue != null
                  ? formatCurrency(portfolioVvvValue, portfolioCurrency)
                  : '—'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {formatNumber(vvvHoldings)} tokens
                {portfolioVvvPrice != null ? ` @ ${formatCurrency(portfolioVvvPrice, portfolioCurrency)}` : ''}
              </p>
            </div>
            <div className="rounded-lg bg-muted/50 p-4">
              <div className="flex items-center gap-2 mb-2">
                <Coins className="w-4 h-4 text-primary" />
                <p className="text-xs text-muted-foreground uppercase tracking-wide">DIEM Value</p>
              </div>
              <p className="text-2xl font-bold">
                {portfolioDiemValue != null
                  ? formatCurrency(portfolioDiemValue, portfolioCurrency)
                  : '—'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {formatNumber(diemHoldings)} tokens
                {portfolioDiemPrice != null ? ` @ ${formatCurrency(portfolioDiemPrice, portfolioCurrency)}` : ''}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}