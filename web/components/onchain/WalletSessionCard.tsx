'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { useWalletBalance, useWalletTransactions } from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DataState } from '@/components/ui/data-state'
import { Badge } from '@/components/ui/badge'
import { formatNumber } from '@/lib/utils'
import { ExternalLink, LogOut, Wallet } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

const TOKEN_KEY = 'vvv:wallet-session-token'

interface EthereumProvider {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>
}

function getProvider(): EthereumProvider | null {
  if (typeof window === 'undefined') return null
  const provider = (window as unknown as { ethereum?: EthereumProvider }).ethereum
  return provider ?? null
}

export function WalletSessionCard() {
  const [token, setToken] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [blocks, setBlocks] = useState(10000)
  const balance = useWalletBalance(token)
  const transactions = useWalletTransactions(token, blocks)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const stored = window.sessionStorage.getItem(TOKEN_KEY)
    if (stored) setToken(stored)
  }, [])

  const connect = async () => {
    setError(null)
    const provider = getProvider()
    if (!provider) {
      setError('No browser wallet detected. Install a Base-compatible wallet extension.')
      return
    }
    setConnecting(true)
    try {
      const accounts = (await provider.request({ method: 'eth_requestAccounts' })) as string[]
      const address = accounts?.[0]
      if (!address) throw new Error('No wallet account was returned')
      const challenge = await api.createWalletChallenge(address)
      const signature = (await provider.request({
        method: 'personal_sign',
        params: [challenge.message, address],
      })) as string
      const session = await api.verifyWalletChallenge(challenge.challenge_id, signature)
      window.sessionStorage.setItem(TOKEN_KEY, session.token)
      setToken(session.token)
      toast.success('Wallet connected (read-only)')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Wallet authentication failed'
      setError(message)
      toast.error(message)
    } finally {
      setConnecting(false)
    }
  }

  const disconnect = async () => {
    const current = token
    setToken(null)
    if (typeof window !== 'undefined') window.sessionStorage.removeItem(TOKEN_KEY)
    if (current) {
      try {
        await api.logoutWallet(current)
      } catch {
        // Session cleanup on the server is best-effort.
      }
    }
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="w-5 h-5" aria-hidden="true" />
            Wallet Session
          </CardTitle>
          <CardDescription>
            Read-only proof of ownership (Base only). Separate from app sign-in; no
            transactions are authorized.
          </CardDescription>
        </div>
        {token ? (
          <button
            type="button"
            onClick={() => { void disconnect() }}
            className="inline-flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent"
          >
            <LogOut className="w-3 h-3" aria-hidden="true" />
            Disconnect
          </button>
        ) : (
          <button
            type="button"
            onClick={() => { void connect() }}
            disabled={connecting}
            className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {connecting ? 'Connecting…' : 'Connect wallet'}
          </button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        {!token && (
          <p className="text-sm text-muted-foreground">
            Connect a browser wallet to view its VVV balance and recent transfers. The app
            session and wallet session are independent.
          </p>
        )}
        {token && balance.isLoading && <DataState kind="loading" title="Loading wallet balance" rows={1} />}
        {token && balance.isError && !balance.data && (
          <DataState kind="error" title="Could not load wallet balance" onRetry={() => { void balance.refetch() }} />
        )}
        {balance.data && (
          <div className="rounded-md border border-border p-4">
            <div className="flex items-center gap-2">
              <Badge variant="success">Read-only</Badge>
              <span className="font-mono text-xs text-muted-foreground">
                {balance.data.address}
              </span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">VVV on-chain balance</p>
            <p className="text-2xl font-bold">
              {balance.data.onchain
                ? formatNumber(balance.data.onchain.vvv_balance, 4)
                : balance.data.onchain_error
                  ? 'Unavailable'
                  : '—'}
            </p>
            {balance.data.holdings && (
              <p className="mt-1 text-xs text-muted-foreground">
                VeniceStats: {formatNumber(balance.data.holdings.vvv_wallet, 4)} VVV wallet ·{' '}
                {formatNumber(balance.data.holdings.svvv_total, 4)} sVVV
              </p>
            )}
          </div>
        )}
        {token && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Recent transfers</p>
              <select
                value={blocks}
                onChange={(event) => setBlocks(Number(event.target.value))}
                className="rounded-md border border-input bg-background px-2 py-1 text-sm"
                aria-label="Wallet transfer block range"
              >
                <option value="1000">1K blocks</option>
                <option value="10000">10K blocks</option>
                <option value="50000">50K blocks</option>
              </select>
            </div>
            {transactions.isLoading && <DataState kind="loading" title="Loading wallet transfers" rows={2} />}
            {transactions.isError && !transactions.data && (
              <DataState kind="error" title="Could not load wallet transfers" onRetry={() => { void transactions.refetch() }} />
            )}
            {transactions.data && transactions.data.transfers.length === 0 && (
              <DataState kind="empty" title="No transfers in this range" />
            )}
            {!!transactions.data?.transfers.length && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Direction</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Transaction</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.data.transfers.slice(0, 10).map((tx) => (
                    <TableRow key={`${tx.tx_hash}-${tx.log_index}`}>
                      <TableCell>{tx.direction === 'in' ? 'In' : 'Out'}</TableCell>
                      <TableCell>{formatNumber(tx.value_human, 4)} VVV</TableCell>
                      <TableCell>
                        {tx.tx_hash && (
                          <a
                            className="inline-flex items-center gap-1 text-primary hover:underline"
                            href={`https://basescan.org/tx/${tx.tx_hash}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {tx.tx_hash.slice(0, 8)}…<ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
