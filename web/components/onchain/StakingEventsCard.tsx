'use client'

import { useState } from 'react'
import { useStakingEvents } from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DataState } from '@/components/ui/data-state'
import { formatNumber } from '@/lib/utils'
import { ArrowDownLeft, ArrowUpRight, ExternalLink, Landmark } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export function StakingEventsCard({ address }: { address?: string | null }) {
  const [blocks, setBlocks] = useState(10000)
  const { data, isLoading, isError, refetch } = useStakingEvents(blocks, address)

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Landmark className="w-5 h-5" aria-hidden="true" />
            Staking Events
          </CardTitle>
          <CardDescription>
            Bounded VVV transfers into and out of the staking contract
            {address ? ' for this wallet' : ''}
          </CardDescription>
        </div>
        <select
          value={blocks}
          onChange={(event) => setBlocks(Number(event.target.value))}
          className="rounded-md border border-input bg-background px-2 py-1 text-sm"
          aria-label="Staking event block range"
        >
          <option value="1000">1K blocks</option>
          <option value="10000">10K blocks</option>
          <option value="50000">50K blocks</option>
        </select>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading && <DataState kind="loading" title="Loading staking events" rows={3} />}
        {isError && !data && (
          <DataState kind="error" title="Could not load staking events" onRetry={() => { void refetch() }} />
        )}
        {isError && data && (
          <DataState kind="stale" title="Showing last loaded staking events" onRetry={() => { void refetch() }} />
        )}
        {data && data.count === 0 && (
          <DataState
            kind="empty"
            title="No staking events in this range"
            description="Try increasing the recent block range."
          />
        )}
        {data && data.count > 0 && (
          <>
            {data.truncated && (
              <p className="text-xs text-amber-500">
                Showing the first {data.count} events; the range contains more.
              </p>
            )}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Direction</TableHead>
                  <TableHead>Counterparty</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Transaction</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.events.map((event) => (
                  <TableRow key={`${event.tx_hash}-${event.log_index}`}>
                    <TableCell>
                      {event.direction === 'stake' ? (
                        <span className="inline-flex items-center gap-1 text-success">
                          <ArrowUpRight className="w-4 h-4" aria-hidden="true" /> Stake
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-destructive">
                          <ArrowDownLeft className="w-4 h-4" aria-hidden="true" /> Unstake
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {event.counterparty.slice(0, 10)}…
                    </TableCell>
                    <TableCell>{formatNumber(event.value_human, 4)} VVV</TableCell>
                    <TableCell>
                      {event.tx_hash && (
                        <a
                          className="inline-flex items-center gap-1 text-primary hover:underline"
                          href={`https://basescan.org/tx/${event.tx_hash}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {event.tx_hash.slice(0, 8)}…<ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="text-xs text-muted-foreground">
              {data.source} · blocks {data.from_block}–{data.to_block}. {data.note}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}
