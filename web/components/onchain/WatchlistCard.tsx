'use client'

import { useId, useState } from 'react'
import {
  useCreateWatchlistItem,
  useDeleteWatchlistItem,
  useWatchlist,
} from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Eye, Plus, Trash2 } from 'lucide-react'

export function WatchlistCard() {
  const formId = useId()
  const { data, isLoading, isError } = useWatchlist()
  const createItem = useCreateWatchlistItem()
  const deleteItem = useDeleteWatchlistItem()
  const [address, setAddress] = useState('')
  const [label, setLabel] = useState('')

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    createItem.mutate(
      { address: address.trim(), label: label.trim() || null },
      {
        onSuccess: () => {
          setAddress('')
          setLabel('')
        },
      },
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Eye className="w-5 h-5" aria-hidden="true" />
          Watchlist
        </CardTitle>
        <CardDescription>Persisted Base wallets (stored with chain and token)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={onSubmit} className="flex flex-col sm:flex-row gap-3">
          <input
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            placeholder="0x… wallet address"
            aria-label="Watchlist wallet address"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="Label (optional)"
            aria-label="Watchlist label"
            className="sm:w-40 rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={createItem.isPending || !address.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            Add
          </button>
        </form>

        {isLoading && <p className="text-sm text-muted-foreground">Loading watchlist…</p>}
        {isError && <p className="text-sm text-destructive">Failed to load watchlist</p>}
        {data && data.items.length === 0 && (
          <p className="text-sm text-muted-foreground">No watched wallets yet.</p>
        )}
        <ul className="space-y-2">
          {data?.items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-3 rounded-md border border-border p-3"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium">{item.label || 'Wallet'}</p>
                <p className="truncate font-mono text-xs text-muted-foreground">
                  {item.chain} · {item.token.toUpperCase()} · {item.address}
                </p>
              </div>
              <button
                type="button"
                onClick={() => deleteItem.mutate(item.id)}
                aria-label={`Remove ${item.address} from watchlist`}
                className="rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
