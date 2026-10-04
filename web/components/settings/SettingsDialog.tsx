'use client'

import { useEffect, useId, useState } from 'react'
import { Settings2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button, Input } from '@/components/ui'
import { useResetSettings, useSettings, useUpdateSettings } from '@/lib/hooks'
import type { VvvHoldingSource } from '@/lib/api'

type SettingsForm = {
  coingecko_holding_amount: string
  diem_holding_amount: string
  vvv_holding_source: VvvHoldingSource
  vvv_wallet_address: string
  benchmark_max_cost_usd: string
  benchmark_enable_billing_reconciliation: boolean
  benchmark_judge_model: string
}

const EMPTY_FORM: SettingsForm = {
  coingecko_holding_amount: '',
  diem_holding_amount: '',
  vvv_holding_source: 'manual',
  vvv_wallet_address: '',
  benchmark_max_cost_usd: '',
  benchmark_enable_billing_reconciliation: false,
  benchmark_judge_model: '',
}

export function SettingsDialog() {
  const [open, setOpen] = useState(false)
  const { data, isLoading } = useSettings()
  const update = useUpdateSettings()
  const reset = useResetSettings()
  const [form, setForm] = useState<SettingsForm>(EMPTY_FORM)
  const billingReconciliationId = useId()
  const holdingSourceId = useId()
  const walletAddressId = useId()

  useEffect(() => {
    if (!data) return
    setForm({
      coingecko_holding_amount: String(data.coingecko_holding_amount),
      diem_holding_amount: String(data.diem_holding_amount),
      vvv_holding_source: data.vvv_holding_source ?? 'manual',
      vvv_wallet_address: data.vvv_wallet_address ?? '',
      benchmark_max_cost_usd: String(data.benchmark_max_cost_usd),
      benchmark_enable_billing_reconciliation: data.benchmark_enable_billing_reconciliation,
      benchmark_judge_model: data.benchmark_judge_model,
    })
  }, [data])

  const updateField = <K extends keyof SettingsForm>(key: K, value: SettingsForm[K]) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    update.mutate({
      coingecko_holding_amount: Number(form.coingecko_holding_amount),
      diem_holding_amount: Number(form.diem_holding_amount),
      vvv_holding_source: form.vvv_holding_source,
      vvv_wallet_address: form.vvv_wallet_address.trim(),
      benchmark_max_cost_usd: Number(form.benchmark_max_cost_usd),
      benchmark_enable_billing_reconciliation: form.benchmark_enable_billing_reconciliation,
      benchmark_judge_model: form.benchmark_judge_model.trim(),
    })
  }

  const textField = (key: keyof SettingsForm, label: string, type = 'text') => (
    <label htmlFor={`settings-${key}`} className="space-y-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <Input
        id={`settings-${key}`}
        type={type}
        value={form[key] as string}
        onChange={(event) => updateField(key, event.target.value)}
      />
    </label>
  )

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        aria-label="Open settings"
      >
        <Settings2 className="w-4 h-4" />
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Settings</DialogTitle>
            <DialogDescription>These values override the deployment environment defaults.</DialogDescription>
          </DialogHeader>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading settings...</p>
          ) : (
            <form onSubmit={submit} className="space-y-5">
              <section className="space-y-3">
                <h3 className="font-medium">Portfolio</h3>
                <p className="text-xs text-muted-foreground">
                  Prices come from VeniceStats; AUD is derived from daily ECB FX rates.
                </p>
                <label htmlFor={holdingSourceId} className="space-y-1 text-sm">
                  <span className="text-muted-foreground">Holdings source</span>
                  <select
                    id={holdingSourceId}
                    value={form.vvv_holding_source}
                    onChange={(event) => updateField('vvv_holding_source', event.target.value as VvvHoldingSource)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="manual">Manual amounts</option>
                    <option value="wallet">Read VVV and DIEM from wallet</option>
                  </select>
                </label>
                {form.vvv_holding_source === 'wallet' && (
                  <label htmlFor={walletAddressId} className="space-y-1 text-sm">
                    <span className="text-muted-foreground">Wallet address (0x…)</span>
                    <Input
                      id={walletAddressId}
                      type="text"
                      placeholder="0x…"
                      value={form.vvv_wallet_address}
                      onChange={(event) => updateField('vvv_wallet_address', event.target.value)}
                    />
                    <span className="text-xs text-muted-foreground">
                      VeniceStats provides VVV, staked sVVV, unclaimed VVV rewards, and wallet/staked DIEM. If the lookup fails, the manual amounts below are used.
                    </span>
                  </label>
                )}
                <div className="grid grid-cols-2 gap-3">
                  {textField('coingecko_holding_amount', form.vvv_holding_source === 'wallet' ? 'VVV fallback amount' : 'VVV holding', 'number')}
                  {textField('diem_holding_amount', form.vvv_holding_source === 'wallet' ? 'DIEM fallback amount' : 'DIEM holding', 'number')}
                </div>
              </section>
              <section className="space-y-3">
                <h3 className="font-medium">Benchmark</h3>
                {textField('benchmark_max_cost_usd', 'Maximum cost (USD)', 'number')}
                {textField('benchmark_judge_model', 'Judge model')}
                <label htmlFor={billingReconciliationId} className="flex items-center gap-2 text-sm">
                  <input
                    id={billingReconciliationId}
                    type="checkbox"
                    checked={form.benchmark_enable_billing_reconciliation}
                    onChange={(event) => updateField('benchmark_enable_billing_reconciliation', event.target.checked)}
                  />
                  Enable billing reconciliation
                </label>
              </section>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => reset.mutate()} disabled={reset.isPending}>
                  Reset defaults
                </Button>
                <Button type="submit" disabled={update.isPending}>
                  {update.isPending ? 'Saving...' : 'Save settings'}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}