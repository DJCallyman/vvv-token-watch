'use client'

import { useState } from 'react'
import { useHolderLookup } from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DataState } from '@/components/ui/data-state'
import { formatNumber } from '@/lib/utils'
import { Users } from 'lucide-react'

export function HolderLookupCard() {
  const [address, setAddress] = useState('')
  const [lookup, setLookup] = useState<string | null>(null)
  const { data, isLoading, isError, refetch } = useHolderLookup(lookup)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="w-5 h-5" aria-hidden="true" />
          Holder Lookup
        </CardTitle>
        <CardDescription>
          Address-specific holdings via VeniceStats. All-holder enumeration is not available.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form
          className="flex flex-col sm:flex-row gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            setLookup(address.trim() || null)
          }}
        >
          <input
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            placeholder="0x…"
            aria-label="Holder address"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <button
            type="submit"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            Look up
          </button>
        </form>

        {lookup && isLoading && <DataState kind="loading" title="Looking up holder" rows={2} />}
        {lookup && isError && !data && (
          <DataState kind="error" title="Could not load holder data" onRetry={() => { void refetch() }} />
        )}
        {data && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-md bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">Wallet VVV</p>
                <p className="font-semibold">{formatNumber(data.holdings.vvv_wallet, 4)}</p>
              </div>
              <div className="rounded-md bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">Staked sVVV</p>
                <p className="font-semibold">{formatNumber(data.holdings.svvv_total, 4)}</p>
              </div>
              <div className="rounded-md bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">Pending rewards</p>
                <p className="font-semibold">{formatNumber(data.holdings.pending_rewards, 4)}</p>
              </div>
              <div className="rounded-md bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">DIEM (wallet + staked)</p>
                <p className="font-semibold">
                  {formatNumber(data.holdings.diem_wallet + data.holdings.diem_staked, 4)}
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              {data.source} · {data.note}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
