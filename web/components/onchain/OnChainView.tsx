'use client'

import { useState } from 'react'
import { useOnchainSupply, useOnchainStaking, useOnchainBalance, useOnchainTransfers } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { formatNumber } from '@/lib/utils'
import { ArrowDownLeft, ArrowUpRight, Blocks, Coins, ExternalLink, Landmark, Search } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export function OnChainView() {
  const { data: supply, isLoading: supplyLoading, isError: supplyError } = useOnchainSupply()
  const { data: staking, isLoading: stakingLoading, isError: stakingError } = useOnchainStaking()
  const [address, setAddress] = useState('')
  const [lookup, setLookup] = useState<string | null>(null)
  const { data: balance, isLoading: balLoading, isError: balError } = useOnchainBalance(lookup)
  const [blocks, setBlocks] = useState(10000)
  const { data: transfers, isLoading: transfersLoading, isError: transfersError } = useOnchainTransfers(lookup, blocks)

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
      {lookup && (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Transfers</CardTitle>
              <CardDescription>VVV transfers involving this wallet</CardDescription>
            </div>
            <select value={blocks} onChange={(e) => setBlocks(Number(e.target.value))} className="rounded-md border border-input bg-background px-2 py-1 text-sm" aria-label="Transfer block range">
              <option value="1000">1K blocks</option>
              <option value="10000">10K blocks</option>
              <option value="50000">50K blocks</option>
            </select>
          </CardHeader>
          <CardContent>
            {transfersLoading && <div className="animate-pulse text-muted-foreground">Loading transfers…</div>}
            {transfersError && <div className="text-destructive text-sm">Failed to load transfers</div>}
            {!transfersLoading && !transfersError && transfers?.transfers.length === 0 && <p className="text-sm text-muted-foreground">No transfers found in this range.</p>}
            {!!transfers?.transfers.length && (
              <Table>
                <TableHeader><TableRow><TableHead>Direction</TableHead><TableHead>From</TableHead><TableHead>To</TableHead><TableHead>Amount</TableHead><TableHead>Transaction</TableHead></TableRow></TableHeader>
                <TableBody>{transfers.transfers.map((tx) => <TableRow key={`${tx.tx_hash}-${tx.log_index}`}>
                  <TableCell>{tx.direction === 'in' ? <ArrowDownLeft className="text-success" aria-label="Incoming" /> : <ArrowUpRight className="text-destructive" aria-label="Outgoing" />}</TableCell>
                  <TableCell className="font-mono text-xs">{tx.from.slice(0, 8)}…</TableCell>
                  <TableCell className="font-mono text-xs">{tx.to.slice(0, 8)}…</TableCell>
                  <TableCell>{formatNumber(tx.value_human, 4)} VVV</TableCell>
                  <TableCell>{tx.tx_hash && <a className="inline-flex items-center gap-1 text-primary hover:underline" href={`https://basescan.org/tx/${tx.tx_hash}`} target="_blank" rel="noreferrer">{tx.tx_hash.slice(0, 8)}…<ExternalLink className="w-3 h-3" /></a>}</TableCell>
                </TableRow>)}</TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
