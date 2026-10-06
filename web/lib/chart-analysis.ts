// Deterministic chart calculations for price history (Slice 2.3).
//
// All functions are pure and sparse-safe: null, undefined, NaN, and Infinity
// points are skipped rather than propagated. Missing indicator warm-up values
// are returned as `null` so a chart can render gaps honestly.

export interface SeriesPoint {
  time: number
  value: number | null | undefined
}

export interface CleanPoint {
  time: number
  value: number
}

export interface AlertAnnotation {
  id: number
  metric: string
  message: string
  triggeredAt: number
  value: number
  alertType: string
}

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

/** Drop points with a non-finite time or value and sort by time ascending. */
export function sanitizeSeries(points: SeriesPoint[]): CleanPoint[] {
  const cleaned: CleanPoint[] = []
  for (const point of points) {
    if (!isFiniteNumber(point.time) || !isFiniteNumber(point.value)) continue
    cleaned.push({ time: point.time, value: point.value })
  }
  cleaned.sort((a, b) => a.time - b.time)
  return cleaned
}

/** Simple moving average. Warm-up positions are null. */
export function computeSMA(points: SeriesPoint[], period: number): Array<number | null> {
  const series = sanitizeSeries(points)
  const result: Array<number | null> = series.map(() => null)
  if (period < 1) return result
  let windowSum = 0
  for (let index = 0; index < series.length; index += 1) {
    windowSum += series[index].value
    if (index >= period) {
      windowSum -= series[index - period].value
    }
    if (index >= period - 1) {
      result[index] = windowSum / period
    }
  }
  return result
}

/** Exponential moving average seeded with the first value. */
export function computeEMA(points: SeriesPoint[], period: number): Array<number | null> {
  const series = sanitizeSeries(points)
  const result: Array<number | null> = series.map(() => null)
  if (period < 1 || series.length === 0) return result
  const alpha = 2 / (period + 1)
  let ema = series[0].value
  result[0] = period === 1 ? ema : null
  for (let index = 1; index < series.length; index += 1) {
    ema = series[index].value * alpha + ema * (1 - alpha)
    if (index >= period - 1) {
      result[index] = ema
    }
  }
  return result
}

/**
 * Wilder's RSI. Returns null until `period` changes are available.
 * A flat window yields 50 (neither overbought nor oversold) rather than NaN.
 */
export function computeRSI(points: SeriesPoint[], period = 14): Array<number | null> {
  const series = sanitizeSeries(points)
  const result: Array<number | null> = series.map(() => null)
  if (period < 1 || series.length <= period) return result

  let gainSum = 0
  let lossSum = 0
  for (let index = 1; index <= period; index += 1) {
    const change = series[index].value - series[index - 1].value
    if (change >= 0) gainSum += change
    else lossSum -= change
  }
  let avgGain = gainSum / period
  let avgLoss = lossSum / period
  result[period] = rsiFromAverages(avgGain, avgLoss)

  for (let index = period + 1; index < series.length; index += 1) {
    const change = series[index].value - series[index - 1].value
    const gain = change > 0 ? change : 0
    const loss = change < 0 ? -change : 0
    avgGain = (avgGain * (period - 1) + gain) / period
    avgLoss = (avgLoss * (period - 1) + loss) / period
    result[index] = rsiFromAverages(avgGain, avgLoss)
  }
  return result
}

function rsiFromAverages(avgGain: number, avgLoss: number): number {
  if (avgGain === 0 && avgLoss === 0) return 50
  if (avgLoss === 0) return 100
  const rs = avgGain / avgLoss
  return 100 - 100 / (1 + rs)
}

/** Percent change between the first and last finite values. */
export function percentChange(points: SeriesPoint[]): number | null {
  const series = sanitizeSeries(points)
  if (series.length < 2) return null
  const first = series[0].value
  if (first === 0) return null
  return ((series[series.length - 1].value - first) / Math.abs(first)) * 100
}

export interface AlignedPoint {
  time: number
  left: number | null
  right: number | null
}

/**
 * Align two series on a shared timeline (union of timestamps, sorted).
 *
 * Each side carries its last known value forward so sparse sampling on one
 * side does not create artificial gaps on the other. Comparison charts use
 * this to guarantee both series share one time range.
 */
export function alignSeries(left: SeriesPoint[], right: SeriesPoint[]): AlignedPoint[] {
  const cleanLeft = sanitizeSeries(left)
  const cleanRight = sanitizeSeries(right)
  const times = Array.from(
    new Set([...cleanLeft.map((p) => p.time), ...cleanRight.map((p) => p.time)]),
  ).sort((a, b) => a - b)

  const result: AlignedPoint[] = []
  let leftIndex = 0
  let rightIndex = 0
  let lastLeft: number | null = null
  let lastRight: number | null = null

  for (const time of times) {
    while (leftIndex < cleanLeft.length && cleanLeft[leftIndex].time <= time) {
      lastLeft = cleanLeft[leftIndex].value
      leftIndex += 1
    }
    while (rightIndex < cleanRight.length && cleanRight[rightIndex].time <= time) {
      lastRight = cleanRight[rightIndex].value
      rightIndex += 1
    }
    result.push({ time, left: lastLeft, right: lastRight })
  }
  return result
}

export interface AlertEventInput {
  id: number
  alert_config_id: number
  triggered_at: string | null
  message: string
  value: number
  acknowledged: boolean
}

export interface AlertConfigInput {
  id: number
  alert_type: string
  metric: string
}

/**
 * Match alert events to a chart window and metric.
 *
 * Only events whose config metric matches the charted metric are returned;
 * events without a parseable timestamp are dropped rather than guessed.
 */
export function matchAlertAnnotations(
  events: AlertEventInput[],
  configs: AlertConfigInput[],
  metric: string,
  rangeStart: number,
  rangeEnd: number,
): AlertAnnotation[] {
  const metricByConfig = new Map<number, AlertConfigInput>()
  for (const config of configs) {
    metricByConfig.set(config.id, config)
  }
  const annotations: AlertAnnotation[] = []
  for (const event of events) {
    const config = metricByConfig.get(event.alert_config_id)
    if (!config || config.metric !== metric) continue
    if (!event.triggered_at) continue
    const triggeredAt = Date.parse(event.triggered_at)
    if (!Number.isFinite(triggeredAt)) continue
    if (triggeredAt < rangeStart || triggeredAt > rangeEnd) continue
    annotations.push({
      id: event.id,
      metric,
      message: event.message,
      triggeredAt,
      value: event.value,
      alertType: config.alert_type,
    })
  }
  return annotations.sort((a, b) => a.triggeredAt - b.triggeredAt)
}
