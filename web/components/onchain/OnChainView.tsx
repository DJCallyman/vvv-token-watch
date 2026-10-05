'use client'

import { useState } from 'react'
import { useOnchainSupply, useOnchainStaking, useOnchainBalance, useOnchainTransfers } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { DataState } from '@/components/ui/data-state'
import { formatNumber } from '@/lib/utils'
import { ArrowDownLeft, ArrowUpRight, Blocks, Coins, ExternalLink, Landmark, Search } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export function OnChainView() {
  const { data: supply, isLoading: supplyLoading, isError: supplyError, refetch: refetchSupply } = useOnchainSupply()
  const { data: staking, isLoading: stakingLoading, isError: stakingError, refetch: refetchStaking } = useOnchainStaking()
  const [address, setAddress] = useState('')
  const [lookup, setLookup] = useState<string | null>(null)
  const { data: balance, isLoading: balLoading, isError: balError, refetch: refetchBalance } = useOnchainBalance(lookup)
  const [blocks, setBlocks] = useState(10000)
  const { data: transfers, isLoading: transfersLoading, isError: transfersError, refetch: refetchTransfers } = useOnchainTransfers(lookup, blocks)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">On-Chain VVV</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Supply &amp; staking via VeniceStats · wallet data via Venice crypto RPC
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
            {supplyLoading && <DataState kind="loading" title="Loading token supply" rows={2} />}
            {supplyError && !supply && <DataState kind="error" title="Could not load token supply" onRetry={() => { void refetchSupply() }} />}
            {supplyError && supply && <DataState kind="stale" title="Showing last loaded supply data" onRetry={() => { void refetchSupply() }} />}
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
                    <p className="text-sm text-muted-foreground">Circulating</p>
                    <p className="text-xl font-semibold">{formatNumber(supply.circulating_estimate, 2)}</p>
                  </div>
                </div>
                {typeof supply.burned_supply === 'number' && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Burned</p>
                      <p className="text-xl font-semibold">{formatNumber(supply.burned_supply, 2)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Free Float (circ.)</p>
                      <p className="text-xl font-semibold">
                        {typeof supply.free_float_pct_circulating === 'number'
                          ? `${formatNumber(supply.free_float_pct_circulating, 1)}%`
                          : '—'}
                      </p>
                    </div>
                  </div>
                )}
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
            {stakingLoading && <DataState kind="loading" title="Loading staking data" rows={2} />}
            {stakingError && !staking && <DataState kind="error" title="Could not load staking data" onRetry={() => { void refetchStaking() }} />}
            {stakingError && staking && <DataState kind="stale" title="Showing last loaded staking data" onRetry={() => { void refetchStaking() }} />}
            {staking && (
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Staked VVV</p>
                  <p className="text-3xl font-bold">{formatNumber(staking.staked_vvv, 2)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">% of Supply Staked</p>
                  <p className="text-xl font-semibold">
                    {typeof staking.staked_percent === 'number'
                      ? `${formatNumber(staking.staked_percent, 2)}%`
                      : '—'}
                  </p>
                  {typeof staking.staked_percent === 'number' && (
                    <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full"
                        style={{ width: `${Math.min(staking.staked_percent, 100)}%` }}
                      />
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {typeof staking.apr === 'number' && (
                    <div>
                      <p className="text-sm text-muted-foreground">Staker APR</p>
                      <p className="text-xl font-semibold">
                        {formatNumber(staking.apr * (staking.apr <= 1 ? 100 : 1), 2)}%
                      </p>
                    </div>
                  )}
                  {typeof staking.lock_ratio === 'number' && (
                    <div>
                      <p className="text-sm text-muted-foreground">Lock Ratio</p>
                      <p className="text-xl font-semibold">{formatNumber(staking.lock_ratio * 100, 1)}%</p>
                    </div>
                  )}
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
          {lookup && balLoading && <DataState kind="loading" title="Looking up wallet balance" rows={1} />}
          {lookup && balError && !balance && <DataState kind="error" title="Could not load wallet balance" onRetry={() => { void refetchBalance() }} />}
          {balError && balance && <DataState kind="stale" title="Showing last loaded wallet balance" onRetry={() => { void refetchBalance() }} />}
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
            {transfersLoading && <DataState kind="loading" title="Loading wallet transfers" rows={3} />}
            {transfersError && !transfers && <DataState kind="error" title="Could not load wallet transfers" onRetry={() => { void refetchTransfers() }} />}
            {transfersError && transfers && <DataState kind="stale" title="Showing last loaded transfers" onRetry={() => { void refetchTransfers() }} />}
            {!transfersLoading && !transfersError && transfers?.transfers.length === 0 && <DataState kind="empty" title="No transfers in this range" description="Try increasing the recent block range." />}
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
