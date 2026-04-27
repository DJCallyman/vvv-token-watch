'use client'

import { usePrices } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { Coins, TrendingUp, Wallet, BarChart3, ArrowUpRight, ArrowDownRight } from 'lucide-react'

export function PricesView() {
  const { data: prices, isLoading, isError } = usePrices()

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

  const vvvValue = prices.portfolio?.vvv_value_usd || (vvvPrice * vvvHoldings)
  const diemValue = prices.portfolio?.diem_value_usd || (diemPrice * diemHoldings)
  const totalValue = prices.portfolio?.total_usd || (vvvValue + diemValue)

  const holdingsRatio = totalValue > 0 ? (vvvValue / totalValue) * 100 : 0

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
              {vvvAud && (
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
                ≈ {formatCurrency(vvvValue)}
              </p>
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
              {diemAud && (
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
                ≈ {formatCurrency(diemValue)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="w-5 h-5" />
            Portfolio Summary
          </CardTitle>
          <CardDescription>Your combined token holdings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="rounded-lg bg-muted/50 p-4">
              <div className="flex items-center gap-2 mb-2">
                <Coins className="w-4 h-4 text-primary" />
                <p className="text-xs text-muted-foreground uppercase tracking-wide">VVV Value</p>
              </div>
              <p className="text-2xl font-bold">{formatCurrency(vvvValue)}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {formatNumber(vvvHoldings)} tokens @ {formatCurrency(vvvPrice)}
              </p>
            </div>
            <div className="rounded-lg bg-muted/50 p-4">
              <div className="flex items-center gap-2 mb-2">
                <Coins className="w-4 h-4 text-primary" />
                <p className="text-xs text-muted-foreground uppercase tracking-wide">DIEM Value</p>
              </div>
              <p className="text-2xl font-bold">{formatCurrency(diemValue)}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {formatNumber(diemHoldings)} tokens @ {formatCurrency(diemPrice)}
              </p>
            </div>
            <div className="rounded-lg bg-primary/10 border border-primary/20 p-4">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Total Value</p>
              </div>
              <p className="text-3xl font-bold text-primary">{formatCurrency(totalValue)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Portfolio Allocation
          </CardTitle>
          <CardDescription>Distribution of your holdings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="h-4 bg-muted rounded-full overflow-hidden flex">
              <div 
                className="h-full bg-primary transition-all"
                style={{ width: `${holdingsRatio}%` }}
              />
              <div 
                className="h-full bg-success transition-all"
                style={{ width: `${100 - holdingsRatio}%` }}
              />
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-primary" />
                  <span className="font-medium">VVV</span>
                </div>
                <div className="text-right">
                  <p className="font-semibold">{holdingsRatio.toFixed(1)}%</p>
                  <p className="text-sm text-muted-foreground">{formatCurrency(vvvValue)}</p>
                </div>
              </div>
              
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-success" />
                  <span className="font-medium">DIEM</span>
                </div>
                <div className="text-right">
                  <p className="font-semibold">{(100 - holdingsRatio).toFixed(1)}%</p>
                  <p className="text-sm text-muted-foreground">{formatCurrency(diemValue)}</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {vvvPrice > 0 && diemPrice > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Token Ratios
            </CardTitle>
            <CardDescription>Exchange relationships between tokens</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-4 rounded-lg bg-muted/50">
                <p className="text-sm text-muted-foreground mb-2">VVV / DIEM Ratio</p>
                <p className="text-2xl font-bold">
                  {diemPrice > 0 ? formatNumber(vvvPrice / diemPrice, 4) : '—'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  1 VVV = {diemPrice > 0 ? formatNumber(vvvPrice / diemPrice, 4) : '—'} DIEM
                </p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <p className="text-sm text-muted-foreground mb-2">DIEM / VVV Ratio</p>
                <p className="text-2xl font-bold">
                  {vvvPrice > 0 ? formatNumber(diemPrice / vvvPrice, 4) : '—'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  1 DIEM = {vvvPrice > 0 ? formatNumber(diemPrice / vvvPrice, 4) : '—'} VVV
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}