'use client'

import { useState } from 'react'
import { useOnchainSupply, useOnchainStaking, useOnchainBalance } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { formatNumber } from '@/lib/utils'
import { Blocks, Coins, Landmark, Search } from 'lucide-react'

export function OnChainView() {
  const { data: supply, isLoading: supplyLoading, isError: supplyError } = useOnchainSupply()
  const { data: staking, isLoading: stakingLoading, isError: stakingError } = useOnchainStaking()
  const [address, setAddress] = useState('')
  const [lookup, setLookup] = useState<string | null>(null)
  const { data: balance, isLoading: balLoading, isError: balError } = useOnchainBalance(lookup)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">On-Chain VVV</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Base network data via Venice crypto RPC
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Coins className="w-5 h-5" />
              Token Supply
            </CardTitle>
            <CardDescription>VVV ERC-20 on Base</CardDescription>
          </CardHeader>
          <CardContent>
            {supplyLoading && (
              <div className="animate-pulse text-muted-foreground">Loading supply…</div>
            )}
            {supplyError && (
              <div className="text-destructive text-sm">Failed to load supply</div>
            )}
            {supply && (
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Supply</p>
                  <p className="text-3xl font-bold">{formatNumber(supply.total_supply, 2)}</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Staked (contract)</p>
                    <p className="text-xl font-semibold">{formatNumber(supply.staked_in_contract, 2)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Circulating (est.)</p>
                    <p className="text-xl font-semibold">{formatNumber(supply.circulating_estimate, 2)}</p>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground break-all">
                  Token: {supply.token_address}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Landmark className="w-5 h-5" />
              Staking Pool
            </CardTitle>
            <CardDescription>Venice staking contract</CardDescription>
          </CardHeader>
          <CardContent>
            {stakingLoading && (
              <div className="animate-pulse text-muted-foreground">Loading staking…</div>
            )}
            {stakingError && (
              <div className="text-destructive text-sm">Failed to load staking</div>
            )}
            {staking && (
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Staked VVV</p>
                  <p className="text-3xl font-bold">{formatNumber(staking.staked_vvv, 2)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">% of Supply Staked</p>
                  <p className="text-xl font-semibold">{formatNumber(staking.staked_percent, 2)}%</p>
                  <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${Math.min(staking.staked_percent, 100)}%` }}
                    />
                  </div>
                </div>
                {staking.note && (
                  <p className="text-xs text-muted-foreground">{staking.note}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Blocks className="w-5 h-5" />
            Wallet Lookup
          </CardTitle>
          <CardDescription>VVV balance for any Base address</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form
            className="flex flex-col sm:flex-row gap-3"
            onSubmit={(e) => {
              e.preventDefault()
              setLookup(address.trim() || null)
            }}
          >
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="0x…"
              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
              aria-label="Wallet address"
            />
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
            >
              <Search className="w-4 h-4" />
              Lookup
            </button>
          </form>
          {balLoading && <div className="animate-pulse text-muted-foreground">Looking up…</div>}
          {balError && <div className="text-destructive text-sm">Failed to load balance</div>}
          {balance && (
            <div className="rounded-md border border-border p-4">
              <p className="text-sm text-muted-foreground">VVV Balance</p>
              <p className="text-2xl font-bold">{formatNumber(balance.vvv_balance, 4)}</p>
              <p className="text-xs text-muted-foreground mt-2 break-all">{balance.address}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
