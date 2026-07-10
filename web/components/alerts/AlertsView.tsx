'use client'

import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAlerts, useAlertEvents } from '@/lib/hooks'
import { api, type AlertConfigCreate } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bell, Check, Plus, Trash2 } from 'lucide-react'

const METRIC_OPTIONS = [
  { value: 'diem_usage_percent', label: 'DIEM usage %' },
  { value: 'usd_usage_percent', label: 'USD usage %' },
  { value: 'diem_balance', label: 'DIEM balance' },
  { value: 'usd_balance', label: 'USD balance' },
  { value: 'vvv_price_usd', label: 'VVV price (USD)' },
  { value: 'diem_price_usd', label: 'DIEM price (USD)' },
]

export function AlertsView() {
  const queryClient = useQueryClient()
  const { data: alertsData, isLoading: alertsLoading, isError: alertsError } = useAlerts()
  const { data: eventsData, isLoading: eventsLoading } = useAlertEvents(false)
  const [form, setForm] = useState<AlertConfigCreate>({
    name: '',
    alert_type: 'usage_percent',
    metric: 'diem_usage_percent',
    threshold: 80,
    comparison: 'gte',
    enabled: true,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['alerts'] })
    queryClient.invalidateQueries({ queryKey: ['alertEvents'] })
  }

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.createAlert(form)
      setForm((f) => ({ ...f, name: '' }))
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create alert')
    } finally {
      setSaving(false)
    }
  }

  const onDelete = async (id: number) => {
    try {
      await api.deleteAlert(id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete alert')
    }
  }

  const onAck = async (id: number) => {
    try {
      await api.acknowledgeAlertEvent(id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to acknowledge event')
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Alerts</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Threshold alerts for usage, balance, and price
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5" />
              Create Alert
            </CardTitle>
            <CardDescription>Configure a threshold to monitor</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onCreate} className="space-y-4">
              <div>
                <label className="text-sm text-muted-foreground">Name</label>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-muted-foreground">Type</label>
                  <select
                    value={form.alert_type}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        alert_type: e.target.value as AlertConfigCreate['alert_type'],
                      })
                    }
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="usage_percent">Usage %</option>
                    <option value="balance_threshold">Balance</option>
                    <option value="price_threshold">Price</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Metric</label>
                  <select
                    value={form.metric}
                    onChange={(e) => setForm({ ...form, metric: e.target.value })}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    {METRIC_OPTIONS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-muted-foreground">Threshold</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={form.threshold}
                    onChange={(e) => setForm({ ...form, threshold: Number(e.target.value) })}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Comparison</label>
                  <select
                    value={form.comparison}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        comparison: e.target.value as 'gte' | 'lte',
                      })
                    }
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="gte">≥ greater or equal</option>
                    <option value="lte">≤ less or equal</option>
                  </select>
                </div>
              </div>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                <Bell className="w-4 h-4" />
                {saving ? 'Saving…' : 'Create alert'}
              </button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Configured Alerts</CardTitle>
            <CardDescription>
              {alertsData ? `${alertsData.count} alert(s)` : '—'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {alertsLoading && (
              <div className="animate-pulse text-muted-foreground">Loading alerts…</div>
            )}
            {alertsError && (
              <div className="text-destructive text-sm">Failed to load alerts</div>
            )}
            {alertsData && alertsData.alerts.length === 0 && (
              <p className="text-sm text-muted-foreground">No alerts configured yet.</p>
            )}
            <ul className="space-y-3">
              {alertsData?.alerts.map((a) => (
                <li
                  key={a.id}
                  className="flex items-start justify-between gap-3 rounded-md border border-border p-3"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{a.name}</span>
                      <Badge variant={a.enabled ? 'success' : 'secondary'}>
                        {a.enabled ? 'On' : 'Off'}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {a.metric} {a.comparison} {a.threshold} · {a.alert_type}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onDelete(a.id)}
                    className="rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    aria-label={`Delete alert ${a.name}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Events</CardTitle>
          <CardDescription>Triggered alerts (acknowledge to clear)</CardDescription>
        </CardHeader>
        <CardContent>
          {eventsLoading && (
            <div className="animate-pulse text-muted-foreground">Loading events…</div>
          )}
          {eventsData && eventsData.events.length === 0 && (
            <p className="text-sm text-muted-foreground">No alert events yet.</p>
          )}
          <ul className="space-y-3">
            {eventsData?.events.map((ev) => (
              <li
                key={ev.id}
                className="flex items-center justify-between gap-3 rounded-md border border-border p-3"
              >
                <div>
                  <p className="text-sm font-medium">{ev.message}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {ev.triggered_at ? new Date(ev.triggered_at).toLocaleString() : '—'}
                    {ev.acknowledged ? ' · acknowledged' : ''}
                  </p>
                </div>
                {!ev.acknowledged && (
                  <button
                    type="button"
                    onClick={() => onAck(ev.id)}
                    className="inline-flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent"
                  >
                    <Check className="w-3 h-3" />
                    Ack
                  </button>
                )}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
