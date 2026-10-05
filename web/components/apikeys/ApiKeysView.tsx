'use client'

import { useId, useState, useMemo } from 'react'
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
} from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { ApiKeyFormModal } from './ApiKeyFormModal'
import { DeleteKeyConfirm } from './DeleteKeyConfirm'
import { formatDate } from '@/lib/utils'
import { Button, Dialog, DialogContent, DialogTitle, Input } from '@/components/ui'
import { DataState } from '@/components/ui/data-state'
import { toast } from 'sonner'
import { useDisplayPreferences } from '@/components/PreferencesProvider'

interface SecretDisplay {
  apiKey: string
  id: string
  description?: string
}

export function ApiKeysView() {
  const { timezone } = useDisplayPreferences()
  const { data, isLoading, isError, refetch } = useAPIKeysUsage()
  const createMutation = useCreateAPIKey()
  const updateMutation = useUpdateAPIKey()
  const deleteMutation = useDeleteAPIKey()

  const [search, setSearch] = useState('')
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

    return result
  }, [keys, search, typeFilter])

  const columns: DataTableColumn<APIKeyUsage>[] = [
    {
      id: 'name',
      header: 'Name',
      sortValue: (key) => key.name,
      cell: (key) => (
        <div className="flex flex-col gap-1">
          <span className="font-medium">{key.name}</span>
          {key.last6_chars && <span className="font-mono text-xs text-muted-foreground">…{key.last6_chars}</span>}
        </div>
      ),
    },
    {
      id: 'type',
      header: 'Type',
      sortValue: (key) => key.api_key_type ?? '',
      cell: (key) => (
        <div className="flex flex-col items-start gap-1">
          {key.api_key_type ? <Badge variant={key.api_key_type === 'ADMIN' ? 'destructive' : 'default'}>{key.api_key_type}</Badge> : '—'}
          {key.model_privacy && <span className="text-xs text-muted-foreground">{key.model_privacy.replaceAll('_', ' ').toLowerCase()}</span>}
        </div>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      sortValue: (key) => key.is_active ? 1 : 0,
      cell: (key) => <Badge variant={key.is_active ? 'success' : 'secondary'}>{key.is_active ? 'Active' : 'Inactive'}</Badge>,
    },
    {
      id: 'usage',
      header: '7-day use',
      sortValue: (key) => key.diem_usage,
      cell: (key) => (
        <span className="text-xs text-muted-foreground">
          ${key.usd_usage.toFixed(2)} USD · {key.diem_usage.toFixed(4)} DIEM
        </span>
      ),
    },
    {
      id: 'limits',
      header: 'Limits / current',
      cell: (key) => {
        const hasLimits = key.consumption_limits_usd != null || key.consumption_limits_diem != null
        return (
          <div className="space-y-1 text-xs text-muted-foreground">
            <div>
              {hasLimits ? (
                <>
                  {key.consumption_limits_usd != null && `$${key.consumption_limits_usd} USD`}
                  {key.consumption_limits_usd != null && key.consumption_limits_diem != null && ' · '}
                  {key.consumption_limits_diem != null && `${key.consumption_limits_diem} DIEM`}
                  {key.limit_period && ` / ${key.limit_period.toLowerCase()}`}
                </>
              ) : 'Unlimited'}
            </div>
            {(key.current_period_usage_usd != null || key.current_period_usage_diem != null) && (
              <div>
                Current: {key.current_period_usage_usd != null && `$${Number(key.current_period_usage_usd).toFixed(2)} USD`}
                {key.current_period_usage_usd != null && key.current_period_usage_diem != null && ' · '}
                {key.current_period_usage_diem != null && `${Number(key.current_period_usage_diem).toFixed(4)} DIEM`}
              </div>
            )}
          </div>
        )
      },
    },
    { id: 'created', header: 'Created', sortValue: (key) => key.created_at, cell: (key) => formatDate(key.created_at, timezone) },
    { id: 'last-used', header: 'Last used', sortValue: (key) => key.last_used_at ?? '', cell: (key) => key.last_used_at ? formatDate(key.last_used_at, timezone) : '—' },
    {
      id: 'actions',
      header: 'Actions',
      hideable: false,
      className: 'text-right',
      cell: (key) => (
        <div className="flex justify-end gap-1">
          <button type="button" onClick={() => setFormState({ mode: 'edit', key })} aria-label={`Edit ${key.name}`} className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <Pencil className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => setDeleteTarget(key)} aria-label={`Delete ${key.name}`} className="rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ]

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
                aria-label="Search API keys"
                placeholder="Search by name or id…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <select
              aria-label="Filter API keys by type"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as typeof typeFilter)}
              className="px-3 py-2 rounded-md border border-input bg-background text-foreground"
            >
              <option value="all">All types</option>
              <option value="INFERENCE">Inference</option>
              <option value="ADMIN">Admin</option>
            </select>
          </div>

          {isLoading && <DataState kind="loading" title="Loading API keys" rows={3} />}

          {isError && !data && (
            <DataState
              kind="error"
              title="Could not load API keys"
              description="Check your connection and try again."
              onRetry={() => { void refetch() }}
              retryLabel="Retry"
            />
          )}

          {isError && data && (
            <DataState
              kind="stale"
              title="Showing last available API-key data"
              description="The latest refresh failed. Your loaded data remains available."
              onRetry={() => { void refetch() }}
            />
          )}

          {!isLoading && data && filteredKeys.length === 0 && (
            <DataState
              kind="empty"
              title={keys.length === 0 ? 'No API keys yet' : 'No keys match these filters'}
              description={keys.length === 0 ? 'Create a key to start tracking per-key usage.' : 'Try a different search or key type.'}
            />
          )}

          {!isLoading && data && filteredKeys.length > 0 && (
            <DataTable
              rows={filteredKeys}
              columns={columns}
              getRowId={(key) => key.id}
              ariaLabel="API keys"
              emptyMessage="No keys match these filters."
              initialSort={{ columnId: 'usage', direction: 'desc' }}
            />
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

function SecretDisplayModal({
  secret,
  onClose,
}: {
  secret: SecretDisplay
  onClose: () => void
}) {
  const [copied, setCopied] = useState(false)
  const titleId = useId()
  const secretInputId = useId()

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(secret.apiKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      toast.success('API key copied')
    } catch {
      toast.error('Unable to copy API key. Select and copy it manually.')
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent aria-labelledby={titleId} className="max-w-lg">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-warning/10 p-2 text-warning">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1 space-y-2">
            <DialogTitle id={titleId} className="text-lg font-semibold">
              Save this API key now
            </DialogTitle>
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
          <label htmlFor={secretInputId} className="text-xs font-medium text-muted-foreground">
            API key secret
          </label>
          <div className="flex items-stretch gap-2">
            <Input
              id={secretInputId}
              readOnly
              value={secret.apiKey}
              className="flex-1 bg-muted font-mono"
              onFocus={(e) => e.currentTarget.select()}
              aria-label="API key secret"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onCopy}
              className={copied ? 'border-success bg-success/10 text-success' : undefined}
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
            </Button>
          </div>
        </div>
        <div className="mt-6 flex justify-end">
          <Button
            type="button"
            onClick={onClose}
          >
            I&apos;ve saved the key
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
