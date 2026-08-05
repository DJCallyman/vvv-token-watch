'use client'

import { useState, useMemo } from 'react'
import { Key, Search, Plus, Pencil, Trash2, AlertTriangle, Check, Copy } from 'lucide-react'
import {
  useAPIKeysUsage,
  useCreateAPIKey,
  useUpdateAPIKey,
  useDeleteAPIKey,
} from '@/lib/hooks'
import type {
  APIKeyUsage,
  ApiKeyCreatePayload,
  ApiKeyCreateResponse,
  ApiKeyType,
  LimitPeriod,
} from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ApiKeyFormModal } from './ApiKeyFormModal'
import { DeleteKeyConfirm } from './DeleteKeyConfirm'
import { formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'

type SortMode = 'name' | 'usage' | 'recent'

interface SecretDisplay {
  apiKey: string
  id: string
  description?: string
}

export function ApiKeysView() {
  const { data, isLoading, isError } = useAPIKeysUsage()
  const createMutation = useCreateAPIKey()
  const updateMutation = useUpdateAPIKey()
  const deleteMutation = useDeleteAPIKey()

  const [search, setSearch] = useState('')
  const [sortMode, setSortMode] = useState<SortMode>('usage')
  const [typeFilter, setTypeFilter] = useState<'all' | 'INFERENCE' | 'ADMIN'>('all')

  const [formState, setFormState] = useState<
    | { mode: 'closed' }
    | { mode: 'create' }
    | { mode: 'edit'; key: APIKeyUsage }
  >({ mode: 'closed' })

  const [deleteTarget, setDeleteTarget] = useState<APIKeyUsage | null>(null)
  const [secret, setSecret] = useState<SecretDisplay | null>(null)
  const [error, setError] = useState<string | null>(null)

  const keys = useMemo(() => data?.keys ?? [], [data])

  const filteredKeys = useMemo(() => {
    let result = [...keys]

    if (search) {
      const lower = search.toLowerCase()
      result = result.filter((k) => {
        return (
          (k.name ?? '').toLowerCase().includes(lower) ||
          (k.last6_chars ?? '').toLowerCase().includes(lower) ||
          (k.id ?? '').toLowerCase().includes(lower)
        )
      })
    }

    if (typeFilter !== 'all') {
      result = result.filter((k) => k.api_key_type === typeFilter)
    }

    result.sort((a, b) => {
      switch (sortMode) {
        case 'name':
          return (a.name ?? '').localeCompare(b.name ?? '')
        case 'recent':
          return (
            new Date(b.created_at ?? 0).getTime() -
            new Date(a.created_at ?? 0).getTime()
          )
        case 'usage':
        default:
          return (b.diem_usage ?? 0) - (a.diem_usage ?? 0)
      }
    })

    return result
  }, [keys, search, typeFilter, sortMode])

  const handleCreate = async (payload: ApiKeyCreatePayload) => {
    setError(null)
    try {
      const result: ApiKeyCreateResponse = await createMutation.mutateAsync(payload)
      setFormState({ mode: 'closed' })
      // Show the one-time secret immediately. Venice only returns it during
      // create; the user must copy it now.
      setSecret({
        apiKey: result.data.apiKey,
        id: result.data.id,
        description: result.data.description ?? payload.description,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create key')
    }
  }

  const handleUpdate = async (payload: ApiKeyCreatePayload & { id: string }) => {
    setError(null)
    try {
      await updateMutation.mutateAsync({
        id: payload.id,
        description: payload.description,
        consumptionLimit: payload.consumptionLimit,
        limitPeriod: payload.limitPeriod,
        expiresAt: payload.expiresAt,
      })
      setFormState({ mode: 'closed' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update key')
    }
  }

  const handleDelete = async (id: string) => {
    setError(null)
    try {
      await deleteMutation.mutateAsync(id)
      setDeleteTarget(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete key')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Key className="w-6 h-6" />
            API Keys
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage Venice API keys, rotation, and consumption limits
          </p>
        </div>
        <button
          type="button"
          onClick={() => setFormState({ mode: 'create' })}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <Plus className="w-4 h-4" />
          Create Key
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Your keys</CardTitle>
          <CardDescription>{filteredKeys.length} key(s)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search by name or id…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as typeof typeFilter)}
              className="px-3 py-2 rounded-md border border-input bg-background text-foreground"
            >
              <option value="all">All types</option>
              <option value="INFERENCE">Inference</option>
              <option value="ADMIN">Admin</option>
            </select>
            <select
              value={sortMode}
              onChange={(e) => setSortMode(e.target.value as SortMode)}
              className="px-3 py-2 rounded-md border border-input bg-background text-foreground"
            >
              <option value="usage">Sort: usage</option>
              <option value="name">Sort: name</option>
              <option value="recent">Sort: newest</option>
            </select>
          </div>

          {isLoading && (
            <div className="animate-pulse text-muted-foreground py-8 text-center">
              Loading API keys…
            </div>
          )}

          {isError && (
            <div className="text-destructive text-sm py-8 text-center">
              Failed to load API keys
            </div>
          )}

          {!isLoading && !isError && filteredKeys.length === 0 && (
            <div className="text-sm text-muted-foreground py-8 text-center">
              {keys.length === 0
                ? 'No API keys yet. Click "Create Key" to add one.'
                : 'No keys match your filters.'}
            </div>
          )}

          {!isLoading && !isError && filteredKeys.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Limits</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last used</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredKeys.map((key) => (
                  <ApiKeyRow
                    key={key.id}
                    apiKey={key}
                    onEdit={() => setFormState({ mode: 'edit', key })}
                    onDelete={() => setDeleteTarget(key)}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {formState.mode === 'create' && (
        <ApiKeyFormModal
          mode="create"
          onClose={() => setFormState({ mode: 'closed' })}
          onSubmit={(payload) => handleCreate(payload as ApiKeyCreatePayload)}
          submitting={createMutation.isPending}
        />
      )}

      {formState.mode === 'edit' && (
        <ApiKeyFormModal
          mode="edit"
          existing={formState.key}
          onClose={() => setFormState({ mode: 'closed' })}
          onSubmit={(payload) =>
            handleUpdate(payload as ApiKeyCreatePayload & { id: string })
          }
          submitting={updateMutation.isPending}
        />
      )}

      {deleteTarget && (
        <DeleteKeyConfirm
          apiKey={deleteTarget}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => handleDelete(deleteTarget.id)}
          submitting={deleteMutation.isPending}
        />
      )}

      {secret && <SecretDisplayModal secret={secret} onClose={() => setSecret(null)} />}
    </div>
  )
}

function ApiKeyRow({
  apiKey,
  onEdit,
  onDelete,
}: {
  apiKey: APIKeyUsage
  onEdit: () => void
  onDelete: () => void
}) {
  const hasLimits =
    apiKey.consumption_limits_usd != null || apiKey.consumption_limits_diem != null

  return (
    <TableRow>
      <TableCell className="font-medium">
        <div className="flex flex-col gap-0.5">
          <span>{apiKey.name}</span>
          {apiKey.last6_chars && (
            <span className="text-xs text-muted-foreground font-mono">
              …{apiKey.last6_chars}
            </span>
          )}
        </div>
      </TableCell>
      <TableCell>
        {apiKey.api_key_type ? (
          <Badge variant={apiKey.api_key_type === 'ADMIN' ? 'destructive' : 'default'}>
            {apiKey.api_key_type}
          </Badge>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </TableCell>
      <TableCell>
        <Badge variant={apiKey.is_active ? 'success' : 'secondary'}>
          {apiKey.is_active ? 'Active' : 'Inactive'}
        </Badge>
      </TableCell>
      <TableCell>
        {hasLimits ? (
          <span className="text-xs text-muted-foreground">
            {apiKey.consumption_limits_usd != null && `$${apiKey.consumption_limits_usd} USD`}
            {apiKey.consumption_limits_usd != null && apiKey.consumption_limits_diem != null && ' · '}
            {apiKey.consumption_limits_diem != null && `${apiKey.consumption_limits_diem} DIEM`}
            {apiKey.limit_period && ` / ${apiKey.limit_period.toLowerCase()}`}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">Unlimited</span>
        )}
      </TableCell>
      <TableCell className="text-sm text-muted-foreground">
        {formatDate(apiKey.created_at)}
      </TableCell>
      <TableCell className="text-sm text-muted-foreground">
        {apiKey.last_used_at ? formatDate(apiKey.last_used_at) : '—'}
      </TableCell>
      <TableCell className="text-right">
        <div className="flex justify-end gap-1">
          <button
            type="button"
            onClick={onEdit}
            aria-label={`Edit ${apiKey.name}`}
            className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            aria-label={`Delete ${apiKey.name}`}
            className="rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </TableCell>
    </TableRow>
  )
}

function SecretDisplayModal({
  secret,
  onClose,
}: {
  secret: SecretDisplay
  onClose: () => void
}) {
  const [copied, setCopied] = useState(false)

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(secret.apiKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard might be unavailable in tests; surface copy state only when it works.
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="secret-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
    >
      <div className="w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-lg">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-warning/10 p-2 text-warning">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1 space-y-2">
            <h2 id="secret-title" className="text-lg font-semibold">
              Save this API key now
            </h2>
            <p className="text-sm text-muted-foreground">
              Venice only shows the full secret once. Copy it to a secure
              password manager before closing this dialog.
            </p>
            {secret.description && (
              <p className="text-xs text-muted-foreground">
                Key: <span className="font-mono">{secret.description}</span>
              </p>
            )}
          </div>
        </div>
        <div className="mt-4 space-y-2">
          <label className="text-xs font-medium text-muted-foreground">
            API key secret
          </label>
          <div className="flex items-stretch gap-2">
            <input
              readOnly
              value={secret.apiKey}
              className="flex-1 rounded-md border border-input bg-muted px-3 py-2 font-mono text-sm"
              onFocus={(e) => e.currentTarget.select()}
              aria-label="API key secret"
            />
            <button
              type="button"
              onClick={onCopy}
              className={cn(
                'inline-flex items-center gap-1 rounded-md border border-border px-3 py-2 text-sm hover:bg-accent',
                copied && 'bg-success/10 border-success text-success',
              )}
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" /> Copied
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" /> Copy
                </>
              )}
            </button>
          </div>
        </div>
        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            I&apos;ve saved the key
          </button>
        </div>
      </div>
    </div>
  )
}
