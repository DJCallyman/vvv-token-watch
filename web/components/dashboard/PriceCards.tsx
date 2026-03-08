'use client'

import { usePrices } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { Coins, TrendingUp } from 'lucide-react'

export function PriceCards() {
  const { data: prices, isLoading, isError } = usePrices()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardContent className="flex items-center justify-center h-32">
              <div className="animate-pulse text-muted-foreground">Loading...</div>
            </CardContent>
          </Card>
        ))}
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
            {formatCurrency(prices.vvv?.usd || 0)}
          </p>
          {prices.vvv?.aud && (
            <p className="text-sm text-muted-foreground">
              {formatCurrency(prices.vvv.aud, 'AUD')}
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
            {formatCurrency(prices.diem?.usd || 0)}
          </p>
          {prices.diem?.aud && (
            <p className="text-sm text-muted-foreground">
              {formatCurrency(prices.diem.aud, 'AUD')}
            </p>
          )}
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="w-4 h-4" />
            Portfolio Value
          </CardTitle>
        </CardHeader>
        <CardContent>
          {prices.portfolio ? (
            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">VVV Holdings</p>
                <p className="text-2xl font-bold text-foreground">
                  {formatCurrency(prices.portfolio.vvv_value_usd)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatNumber(prices.holdings.vvv)} VVV @ {formatCurrency(prices.vvv?.usd || 0)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">DIEM Holdings</p>
                <p className="text-2xl font-bold text-foreground">
                  {formatCurrency(prices.portfolio.diem_value_usd)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatNumber(prices.holdings.diem)} DIEM @ {formatCurrency(prices.diem?.usd || 0)}
                </p>
              </div>
              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Total</p>
                <p className="text-lg font-semibold text-foreground">
                  {formatCurrency(prices.portfolio.total_usd)}
                </p>
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