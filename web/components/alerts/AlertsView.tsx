'use client'

import { useId, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAlertEvents, useAlertVoice, useAlerts } from '@/lib/hooks'
import { api, ALERT_METRICS, type AlertConfigCreate, type AlertType } from '@/lib/api'
import { validateAlertInput } from '@/lib/alert-validation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bell, Check, Plus, Trash2, Volume2 } from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime } from '@/lib/utils'
import { useDisplayPreferences } from '@/components/PreferencesProvider'
import { NotificationChannels } from '@/components/alerts/NotificationChannels'
import { ExportMenu } from '@/components/ui/export-menu'

const ALERT_TYPE_OPTIONS: Array<{ value: AlertType; label: string }> = [
  { value: 'usage_percent', label: 'Usage %' },
  { value: 'balance_threshold', label: 'Balance' },
  { value: 'price_threshold', label: 'Price' },
  { value: 'rate_of_change', label: 'Rate of change' },
  { value: 'anomaly', label: 'Anomaly' },
]

export function AlertsView() {
  const formId = useId()
  const { timezone } = useDisplayPreferences()
  const queryClient = useQueryClient()
  const { data: alertsData, isLoading: alertsLoading, isError: alertsError } = useAlerts()
  const { data: eventsData, isLoading: eventsLoading } = useAlertEvents(false)
  const alertVoice = useAlertVoice()
  const [form, setForm] = useState<AlertConfigCreate>({
    name: '',
    alert_type: 'usage_percent',
    metric: 'diem_usage_percent',
    threshold: 80,
    comparison: 'gte',
    enabled: true,
    window_seconds: 3600,
    min_samples: 10,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['alerts'] })
    queryClient.invalidateQueries({ queryKey: ['alertEvents'] })
  }

  const changeAlertType = (alertType: AlertType) => {
    const metrics = ALERT_METRICS[alertType]
    setForm((current) => ({
      ...current,
      alert_type: alertType,
      metric: metrics[0]?.value ?? current.metric,
    }))
  }

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const validationError = validateAlertInput({
      name: form.name,
      alert_type: form.alert_type,
      metric: form.metric,
      threshold: Number(form.threshold),
      comparison: form.comparison ?? 'gte',
      window_seconds: form.window_seconds,
      min_samples: form.min_samples,
    })
    if (validationError) {
      setError(validationError)
      toast.error(validationError)
      return
    }
    setSaving(true)
    try {
      const payload: AlertConfigCreate = {
        name: form.name,
        alert_type: form.alert_type,
        metric: form.metric,
        threshold: Number(form.threshold),
        comparison: form.comparison ?? 'gte',
        enabled: form.enabled ?? true,
      }
      if (form.alert_type === 'rate_of_change') {
        payload.window_seconds = form.window_seconds ?? 3600
      }
      if (form.alert_type === 'anomaly') {
        payload.min_samples = form.min_samples ?? 10
      }
      await api.createAlert(payload)
      setForm((f) => ({ ...f, name: '' }))
      refresh()
      toast.success('Alert created')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create alert'
      setError(message)
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  const onDelete = async (id: number) => {
    try {
      await api.deleteAlert(id)
      refresh()
      toast.success('Alert deleted')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete alert'
      setError(message)
      toast.error(message)
    }
  }

  const onAck = async (id: number) => {
    try {
      await api.acknowledgeAlertEvent(id)
      refresh()
      toast.success('Alert acknowledged')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to acknowledge event'
      setError(message)
      toast.error(message)
    }
  }

  const metrics = ALERT_METRICS[form.alert_type] ?? []

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Alerts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Threshold, rate-of-change, and anomaly alerts for usage, balance, and price
          </p>
        </div>
        <ExportMenu
          name="alerts"
          snapshot={() => ({
            configs: alertsData?.alerts ?? [],
            events: eventsData?.events ?? [],
          })}
          rows={() =>
            (eventsData?.events ?? []).map((event) => ({
              id: event.id,
              alert_config_id: event.alert_config_id,
              triggered_at: event.triggered_at,
              message: event.message,
              value: event.value,
              acknowledged: event.acknowledged,
            }))
          }
        />
      </div>

      {error && (
        <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
          <CardTitle className="flex items-center gap-2" aria-live="polite">
              <Plus className="w-5 h-5" />
              Create Alert
            </CardTitle>
            <CardDescription>Configure a threshold or signal alert to monitor</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onCreate} className="space-y-4">
              <div>
                <label htmlFor={`${formId}-name`} className="text-sm text-muted-foreground">Name</label>
                <input
                  id={`${formId}-name`}
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor={`${formId}-type`} className="text-sm text-muted-foreground">Type</label>
                  <select
                    id={`${formId}-type`}
                    value={form.alert_type}
                    onChange={(e) => changeAlertType(e.target.value as AlertType)}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    {ALERT_TYPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor={`${formId}-metric`} className="text-sm text-muted-foreground">Metric</label>
                  <select
                    id={`${formId}-metric`}
                    value={form.metric}
                    onChange={(e) => setForm({ ...form, metric: e.target.value })}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    {metrics.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor={`${formId}-threshold`} className="text-sm text-muted-foreground">
                    {form.alert_type === 'rate_of_change'
                      ? 'Threshold (% change)'
                      : form.alert_type === 'anomaly'
                        ? 'Threshold (z-score)'
                        : 'Threshold'}
                  </label>
                  <input
                    id={`${formId}-threshold`}
                    type="number"
                    step="any"
                    required
                    value={form.threshold}
                    onChange={(e) => setForm({ ...form, threshold: Number(e.target.value) })}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor={`${formId}-comparison`} className="text-sm text-muted-foreground">Comparison</label>
                  <select
                    id={`${formId}-comparison`}
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
              {form.alert_type === 'rate_of_change' && (
                <div>
                  <label htmlFor={`${formId}-window`} className="text-sm text-muted-foreground">
                    Window (seconds)
                  </label>
                  <input
                    id={`${formId}-window`}
                    type="number"
                    min={60}
                    max={2592000}
                    step={60}
                    value={form.window_seconds ?? 3600}
                    onChange={(e) => setForm({ ...form, window_seconds: Number(e.target.value) })}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                  <span className="text-xs text-muted-foreground">
                    Percent change versus the value at least this far back. Default 3600s.
                  </span>
                </div>
              )}
              {form.alert_type === 'anomaly' && (
                <div>
                  <label htmlFor={`${formId}-samples`} className="text-sm text-muted-foreground">
                    Minimum baseline samples
                  </label>
                  <input
                    id={`${formId}-samples`}
                    type="number"
                    min={2}
                    max={1000}
                    value={form.min_samples ?? 10}
                    onChange={(e) => setForm({ ...form, min_samples: Number(e.target.value) })}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                  <span className="text-xs text-muted-foreground">
                    Z-score versus the mean of earlier samples. Default 10. Zero-variance
                    baselines are skipped, never fired.
                  </span>
                </div>
              )}
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
              <div role="region" aria-label="Loading configured alerts" aria-busy="true" className="animate-pulse space-y-3">
                {[0, 1, 2].map((item) => (
                  <div key={item} className="flex items-center justify-between gap-3 rounded-md border border-border p-3">
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-2/5 rounded bg-muted" />
                      <div className="h-3 w-3/5 rounded bg-muted" />
                    </div>
                    <div className="h-8 w-8 rounded bg-muted" />
                  </div>
                ))}
              </div>
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
                      {a.alert_type === 'rate_of_change' && a.window_seconds != null
                        ? ` · ${a.window_seconds}s window`
                        : ''}
                      {a.alert_type === 'anomaly' && a.min_samples != null
                        ? ` · min ${a.min_samples} samples`
                        : ''}
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

      <NotificationChannels />

      <Card>
        <CardHeader>
          <CardTitle>Recent Events</CardTitle>
          <CardDescription>Triggered alerts (acknowledge to clear)</CardDescription>
        </CardHeader>
        <CardContent>
          {eventsLoading && (
            <div role="region" aria-label="Loading recent alert events" aria-busy="true" className="animate-pulse space-y-3">
              {[0, 1, 2].map((item) => (
                <div key={item} className="flex items-center justify-between gap-3 rounded-md border border-border p-3">
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-3/4 rounded bg-muted" />
                    <div className="h-3 w-2/5 rounded bg-muted" />
                  </div>
                  <div className="h-7 w-14 rounded bg-muted" />
                </div>
              ))}
            </div>
          )}
          {eventsData && eventsData.events.length === 0 && (
            <p className="text-sm text-muted-foreground">No alert events yet.</p>
          )}
          <ul className="space-y-3">
            {eventsData?.events.map((ev) => (
              <li
                key={ev.id}
                id={`event-${ev.id}`}
                className="flex items-center justify-between gap-3 rounded-md border border-border p-3 scroll-mt-20"
              >
                <div>
                  <p className="text-sm font-medium">{ev.message}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {ev.triggered_at ? formatDateTime(ev.triggered_at, timezone) : '—'}
                    {ev.acknowledged ? ' · acknowledged' : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => alertVoice.mutate(ev.id)}
                    disabled={alertVoice.isPending}
                    className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1.5 text-xs hover:bg-accent disabled:opacity-50"
                    aria-label={`Play voice for event ${ev.id}`}
                  >
                    <Volume2 className="w-3 h-3" />
                    Voice
                  </button>
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
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
