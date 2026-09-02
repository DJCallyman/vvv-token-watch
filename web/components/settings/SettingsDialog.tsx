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

type SettingsForm = {
  coingecko_token_id: string
  coingecko_currencies: string
  coingecko_holding_amount: string
  diem_token_id: string
  diem_holding_amount: string
  benchmark_max_cost_usd: string
  benchmark_enable_billing_reconciliation: boolean
  benchmark_judge_model: string
}

const EMPTY_FORM: SettingsForm = {
  coingecko_token_id: '',
  coingecko_currencies: '',
  coingecko_holding_amount: '',
  diem_token_id: '',
  diem_holding_amount: '',
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

  useEffect(() => {
    if (!data) return
    setForm({
      coingecko_token_id: data.coingecko_token_id,
      coingecko_currencies: data.coingecko_currencies.join(', '),
      coingecko_holding_amount: String(data.coingecko_holding_amount),
      diem_token_id: data.diem_token_id,
      diem_holding_amount: String(data.diem_holding_amount),
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
      coingecko_token_id: form.coingecko_token_id.trim(),
      coingecko_currencies: form.coingecko_currencies.split(',').map((value) => value.trim()).filter(Boolean),
      coingecko_holding_amount: Number(form.coingecko_holding_amount),
      diem_token_id: form.diem_token_id.trim(),
      diem_holding_amount: Number(form.diem_holding_amount),
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
                {textField('coingecko_token_id', 'VVV CoinGecko ID')}
                {textField('diem_token_id', 'DIEM CoinGecko ID')}
                {textField('coingecko_currencies', 'Currencies (comma-separated)')}
                <div className="grid grid-cols-2 gap-3">
                  {textField('coingecko_holding_amount', 'VVV holding', 'number')}
                  {textField('diem_holding_amount', 'DIEM holding', 'number')}
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