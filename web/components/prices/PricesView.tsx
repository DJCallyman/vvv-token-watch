'use client'

import { usePrices } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { Coins, TrendingUp, Wallet } from 'lucide-react'

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

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-foreground">Token Prices</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Coins className="w-5 h-5" />
              VVV Token
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Price (USD)</p>
              <p className="text-4xl font-bold text-foreground">
                {formatCurrency(prices.vvv?.usd || 0)}
              </p>
            </div>
            {prices.vvv?.aud && (
              <div>
                <p className="text-sm text-muted-foreground">Price (AUD)</p>
                <p className="text-2xl font-semibold text-foreground">
                  {formatCurrency(prices.vvv.aud, 'AUD')}
                </p>
              </div>
            )}
            <div>
              <p className="text-sm text-muted-foreground">Your Holdings</p>
              <p className="text-xl font-semibold text-foreground">
                {formatNumber(prices.holdings.vvv)} VVV
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
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Price (USD)</p>
              <p className="text-4xl font-bold text-foreground">
                {formatCurrency(prices.diem?.usd || 0)}
              </p>
            </div>
            {prices.diem?.aud && (
              <div>
                <p className="text-sm text-muted-foreground">Price (AUD)</p>
                <p className="text-2xl font-semibold text-foreground">
                  {formatCurrency(prices.diem.aud, 'AUD')}
                </p>
              </div>
            )}
            <div>
              <p className="text-sm text-muted-foreground">Your Holdings</p>
              <p className="text-xl font-semibold text-foreground">
                {formatNumber(prices.holdings.diem)} DIEM
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {prices.portfolio && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="w-5 h-5" />
              Portfolio Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-muted-foreground">VVV Value</p>
                <p className="text-2xl font-bold text-foreground">
                  {formatCurrency(prices.portfolio.vvv_value_usd)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">DIEM Value</p>
                <p className="text-2xl font-bold text-foreground">
                  {formatCurrency(prices.portfolio.diem_value_usd)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Value</p>
                <p className="text-3xl font-bold text-primary">
                  {formatCurrency(prices.portfolio.total_usd)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}