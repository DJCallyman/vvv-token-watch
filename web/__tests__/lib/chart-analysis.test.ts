import {
  alignSeries,
  computeEMA,
  computeRSI,
  computeSMA,
  matchAlertAnnotations,
  percentChange,
  sanitizeSeries,
} from '@/lib/chart-analysis'

const point = (time: number, value: number | null) => ({ time, value })

describe('sanitizeSeries', () => {
  it('drops null, undefined, NaN, and Infinity points and sorts by time', () => {
    const cleaned = sanitizeSeries([
      point(3, 30),
      point(1, 10),
      point(2, null),
      { time: Number.NaN, value: 5 },
      point(4, Number.POSITIVE_INFINITY),
      point(5, 50),
    ])
    expect(cleaned).toEqual([
      { time: 1, value: 10 },
      { time: 3, value: 30 },
      { time: 5, value: 50 },
    ])
  })

  it('handles empty and all-invalid input', () => {
    expect(sanitizeSeries([])).toEqual([])
    expect(sanitizeSeries([point(1, null)])).toEqual([])
  })
})

describe('computeSMA', () => {
  it('returns nulls during warm-up and averages after', () => {
    const result = computeSMA([point(1, 10), point(2, 20), point(3, 30), point(4, 40)], 3)
    expect(result).toEqual([null, null, 20, 30])
  })

  it('skips sparse points instead of treating them as zero', () => {
    const result = computeSMA([point(1, 10), point(2, null), point(3, 30)], 2)
    expect(result).toEqual([null, 20])
  })
})

describe('computeEMA', () => {
  it('seeds after the warm-up window', () => {
    const result = computeEMA([point(1, 10), point(2, 20), point(3, 30)], 2)
    expect(result[0]).toBeNull()
    expect(result[1]).toBeCloseTo(16.6667, 3)
    expect(result[2]).toBeCloseTo(25.5556, 3)
  })
})

describe('computeRSI', () => {
  it('returns 100 for an unbroken gain streak', () => {
    const points = Array.from({ length: 16 }, (_, index) => point(index, 100 + index))
    const result = computeRSI(points, 14)
    expect(result[14]).toBeCloseTo(100)
  })

  it('returns null when there is insufficient history', () => {
    const result = computeRSI([point(1, 10), point(2, 12)], 14)
    expect(result.every((value) => value === null)).toBe(true)
  })

  it('returns 50 for a flat series', () => {
    const points = Array.from({ length: 20 }, (_, index) => point(index, 100))
    const result = computeRSI(points, 14)
    expect(result[14]).toBeCloseTo(50)
  })
})

describe('percentChange', () => {
  it('computes change from first to last finite value', () => {
    expect(percentChange([point(1, 100), point(2, null), point(3, 110)])).toBeCloseTo(10)
  })

  it('returns null for single points or zero base', () => {
    expect(percentChange([point(1, 100)])).toBeNull()
    expect(percentChange([point(1, 0), point(2, 5)])).toBeNull()
  })
})

describe('alignSeries', () => {
  it('shares one timeline and carries values forward', () => {
    const aligned = alignSeries([point(1, 10), point(3, 30)], [point(2, 200), point(3, 300)])
    expect(aligned.map((entry) => entry.time)).toEqual([1, 2, 3])
    expect(aligned[0]).toEqual({ time: 1, left: 10, right: null })
    expect(aligned[1]).toEqual({ time: 2, left: 10, right: 200 })
    expect(aligned[2]).toEqual({ time: 3, left: 30, right: 300 })
  })

  it('handles an empty side without inventing values', () => {
    const aligned = alignSeries([point(1, 10)], [])
    expect(aligned).toEqual([{ time: 1, left: 10, right: null }])
  })
})

describe('matchAlertAnnotations', () => {
  const configs = [
    { id: 1, alert_type: 'price_threshold', metric: 'vvv_price_usd' },
    { id: 2, alert_type: 'anomaly', metric: 'diem_price_usd' },
  ]

  it('matches metric and time range and links event ids', () => {
    const events = [
      { id: 10, alert_config_id: 1, triggered_at: '2026-01-01T10:00:00Z', message: 'a', value: 1.5, acknowledged: false },
      { id: 11, alert_config_id: 2, triggered_at: '2026-01-01T10:00:00Z', message: 'b', value: 2, acknowledged: false },
      { id: 12, alert_config_id: 1, triggered_at: '2025-12-01T10:00:00Z', message: 'old', value: 1, acknowledged: false },
      { id: 13, alert_config_id: 1, triggered_at: null, message: 'no ts', value: 1, acknowledged: false },
    ]
    const start = Date.parse('2026-01-01T00:00:00Z')
    const end = Date.parse('2026-01-02T00:00:00Z')
    const annotations = matchAlertAnnotations(events, configs, 'vvv_price_usd', start, end)
    expect(annotations).toHaveLength(1)
    expect(annotations[0].id).toBe(10)
    expect(annotations[0].alertType).toBe('price_threshold')
  })

  it('returns empty for an unconfigured metric or invalid timestamps', () => {
    const events = [
      { id: 10, alert_config_id: 1, triggered_at: 'not-a-date', message: 'a', value: 1.5, acknowledged: false },
    ]
    expect(matchAlertAnnotations(events, configs, 'vvv_price_usd', 0, Date.now())).toEqual([])
    expect(matchAlertAnnotations(events, configs, 'usd_balance', 0, Date.now())).toEqual([])
  })
})
