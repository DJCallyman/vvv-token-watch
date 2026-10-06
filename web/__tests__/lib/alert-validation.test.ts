import { validateAlertInput } from '@/lib/alert-validation'

const base = {
  name: 'test',
  alert_type: 'usage_percent' as const,
  metric: 'diem_usage_percent',
  threshold: 80,
  comparison: 'gte' as const,
}

describe('validateAlertInput', () => {
  it('accepts valid threshold alerts', () => {
    expect(validateAlertInput(base)).toBeNull()
  })

  it('requires a name', () => {
    expect(validateAlertInput({ ...base, name: '  ' })).toMatch(/name/i)
  })

  it('rejects metrics that do not belong to the alert type', () => {
    expect(validateAlertInput({ ...base, metric: 'vvv_price_usd' })).toMatch(/not valid/i)
  })

  it('validates rate-of-change windows', () => {
    const roc = { ...base, alert_type: 'rate_of_change' as const, metric: 'vvv_price_usd' }
    expect(validateAlertInput({ ...roc, window_seconds: 3600 })).toBeNull()
    expect(validateAlertInput({ ...roc, window_seconds: 10 })).toMatch(/window/i)
    expect(validateAlertInput({ ...roc, window_seconds: 3_000_000 })).toMatch(/window/i)
  })

  it('validates anomaly minimum samples', () => {
    const anomaly = { ...base, alert_type: 'anomaly' as const, metric: 'diem_balance' }
    expect(validateAlertInput({ ...anomaly, min_samples: 10 })).toBeNull()
    expect(validateAlertInput({ ...anomaly, min_samples: 1 })).toMatch(/samples/i)
    expect(validateAlertInput({ ...anomaly, min_samples: 5000 })).toMatch(/samples/i)
  })

  it('rejects non-finite thresholds', () => {
    expect(validateAlertInput({ ...base, threshold: Number.NaN })).toMatch(/threshold/i)
  })
})
