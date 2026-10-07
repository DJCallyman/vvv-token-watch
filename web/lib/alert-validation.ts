import { ALERT_METRICS, type AlertType } from '@/lib/api'

export interface AlertFormInput {
  name: string
  alert_type: AlertType
  metric: string
  threshold: number
  comparison: 'gte' | 'lte'
  window_seconds?: number | null
  min_samples?: number | null
}

/** Client-side validation mirroring the backend alert definition rules. */
export function validateAlertInput(input: AlertFormInput): string | null {
  if (!input.name.trim()) return 'Name is required'
  const allowed = ALERT_METRICS[input.alert_type]
  if (!allowed) return `Unknown alert type '${input.alert_type}'`
  if (!allowed.some((option) => option.value === input.metric)) {
    return `Metric '${input.metric}' is not valid for ${input.alert_type}`
  }
  if (!Number.isFinite(input.threshold)) return 'Threshold must be a number'
  if (input.alert_type === 'rate_of_change') {
    const window = input.window_seconds
    if (window != null && (window < 60 || window > 2_592_000)) {
      return 'Window must be between 60 and 2592000 seconds'
    }
  }
  if (input.alert_type === 'anomaly') {
    const minSamples = input.min_samples
    if (minSamples != null && (minSamples < 2 || minSamples > 1000)) {
      return 'Minimum samples must be between 2 and 1000'
    }
  }
  return null
}
