'use client'

import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import type {
  APIKeyUsage,
  ApiKeyCreatePayload,
  ApiKeyType,
  ConsumptionLimitInput,
  LimitPeriod,
} from '@/lib/api'

type FormPayload = Omit<ApiKeyCreatePayload, 'apiKeyType'> & {
  apiKeyType: ApiKeyType
}

export interface ApiKeyFormModalProps {
  mode: 'create' | 'edit'
  existing?: APIKeyUsage
  onClose: () => void
  onSubmit: (payload: FormPayload & { id?: string }) => void
  submitting?: boolean
}

const TYPES: { value: ApiKeyType; label: string; description: string }[] = [
  {
    value: 'INFERENCE',
    label: 'Inference',
    description: 'Standard, inference-only access',
  },
  {
    value: 'ADMIN',
    label: 'Admin',
    description: 'Full API access including billing/usage',
  },
]

const PERIODS: { value: LimitPeriod; label: string }[] = [
  { value: 'EPOCH', label: 'Per epoch (24h)' },
  { value: 'MONTH', label: 'Per calendar month' },
  { value: 'LIFETIME', label: 'Lifetime cap' },
]

export function ApiKeyFormModal({
  mode,
  existing,
  onClose,
  onSubmit,
  submitting,
}: ApiKeyFormModalProps) {
  const [apiKeyType, setApiKeyType] = useState<ApiKeyType>(
    existing?.api_key_type === 'ADMIN' ? 'ADMIN' : 'INFERENCE',
  )
  const [description, setDescription] = useState<string>(existing?.name ?? '')
  const [limitPeriod, setLimitPeriod] = useState<LimitPeriod | ''>(
    (existing?.limit_period as LimitPeriod | undefined) ?? '',
  )
  const [consumptionLimit, setConsumptionLimit] = useState<ConsumptionLimitInput>({
    usd: existing?.consumption_limits_usd ?? null,
    diem: existing?.consumption_limits_diem ?? null,
  })
  const [expiresAt, setExpiresAt] = useState<string>(existing?.expires_at ?? '')

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, submitting])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedDescription = description.trim()
    if (!trimmedDescription || trimmedDescription.length > 64) {
      return
    }
    const payload: FormPayload & { id?: string } = {
      apiKeyType,
      description: trimmedDescription,
      consumptionLimit:
        consumptionLimit.usd != null || consumptionLimit.diem != null
          ? {
              usd: consumptionLimit.usd ?? null,
              diem: consumptionLimit.diem ?? null,
            }
          : null,
      limitPeriod: limitPeriod || null,
      expiresAt: expiresAt || null,
    }
    if (mode === 'edit' && existing) {
      payload.id = existing.id
    }
    onSubmit(payload)
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="apikey-form-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4"
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg rounded-lg border border-border bg-card shadow-lg"
      >
        <div className="flex items-center justify-between border-b border-border p-4">
          <h2 id="apikey-form-title" className="text-lg font-semibold">
            {mode === 'create' ? 'Create API key' : 'Edit API key'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            disabled={submitting}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4 p-4">
          <div>
            <label className="text-sm font-medium text-foreground" htmlFor="apikey-description">
              Description <span className="text-destructive">*</span>
            </label>
            <input
              id="apikey-description"
              required
              minLength={1}
              maxLength={64}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. CI runner, mobile-app, dev laptop"
              autoFocus
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground mt-1">
              {description.length}/64 characters
            </p>
          </div>

          <fieldset>
            <legend className="text-sm font-medium text-foreground">Type</legend>
            <div className="mt-2 space-y-2">
              {TYPES.map((t) => (
                <label
                  key={t.value}
                  className={`flex items-start gap-2 rounded-md border p-3 cursor-pointer ${
                    apiKeyType === t.value
                      ? 'border-primary bg-primary/5'
                      : 'border-input hover:bg-accent'
                  }`}
                >
                  <input
                    type="radio"
                    name="apiKeyType"
                    value={t.value}
                    checked={apiKeyType === t.value}
                    onChange={() => setApiKeyType(t.value)}
                    disabled={mode === 'edit'}
                    className="mt-1"
                  />
                  <div>
                    <div className="text-sm font-medium">{t.label}</div>
                    <div className="text-xs text-muted-foreground">{t.description}</div>
                  </div>
                </label>
              ))}
            </div>
            {mode === 'edit' && (
              <p className="text-xs text-muted-foreground mt-2">
                Key type cannot be changed after creation.
              </p>
            )}
          </fieldset>

          <fieldset>
            <legend className="text-sm font-medium text-foreground">
              Consumption limits (optional)
            </legend>
            <p className="text-xs text-muted-foreground mt-1">
              Cap the spending per key. Leave both blank for unlimited.
            </p>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <div>
                <label
                  className="text-xs text-muted-foreground"
                  htmlFor="apikey-limit-usd"
                >
                  USD
                </label>
                <input
                  id="apikey-limit-usd"
                  type="number"
                  min={0}
                  step="any"
                  value={consumptionLimit.usd ?? ''}
                  onChange={(e) =>
                    setConsumptionLimit({
                      ...consumptionLimit,
                      usd: e.target.value === '' ? null : Number(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label
                  className="text-xs text-muted-foreground"
                  htmlFor="apikey-limit-diem"
                >
                  DIEM
                </label>
                <input
                  id="apikey-limit-diem"
                  type="number"
                  min={0}
                  step="any"
                  value={consumptionLimit.diem ?? ''}
                  onChange={(e) =>
                    setConsumptionLimit({
                      ...consumptionLimit,
                      diem: e.target.value === '' ? null : Number(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
            <div className="mt-3">
              <label
                className="text-xs text-muted-foreground"
                htmlFor="apikey-limit-period"
              >
                Reset period
              </label>
              <select
                id="apikey-limit-period"
                value={limitPeriod}
                onChange={(e) => setLimitPeriod(e.target.value as LimitPeriod | '')}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">No limit</option>
                {PERIODS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </fieldset>

          <div>
            <label
              className="text-sm font-medium text-foreground"
              htmlFor="apikey-expires"
            >
              Expires (optional)
            </label>
            <input
              id="apikey-expires"
              type="date"
              value={
                expiresAt ? new Date(expiresAt).toISOString().slice(0, 10) : ''
              }
              onChange={(e) => setExpiresAt(e.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Leave blank for no expiry.
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-border p-4">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="rounded-md border border-border px-4 py-2 text-sm hover:bg-accent disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !description.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {submitting
              ? 'Saving…'
              : mode === 'create'
                ? 'Create key'
                : 'Save changes'}
          </button>
        </div>
      </form>
    </div>
  )
}
