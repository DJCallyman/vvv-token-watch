import { cn, formatCurrency, formatNumber, formatPercent } from '@/lib/utils'

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('a', 'b')).toBe('a b')
  })

  it('handles conditional classes', () => {
    expect(cn('base', { active: true, disabled: false })).toBe('base active')
  })

  it('deduplicates conflicting Tailwind classes, keeping last', () => {
    // tailwind-merge picks the last of conflicting utility classes
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500')
  })

  it('handles undefined values gracefully', () => {
    expect(cn('a', undefined, 'b')).toBe('a b')
  })

  it('handles empty input', () => {
    expect(cn()).toBe('')
  })
})

describe('formatCurrency', () => {
  it('formats a positive USD amount', () => {
    expect(formatCurrency(1234.56)).toBe('$1,234.56')
  })

  it('formats zero as USD', () => {
    expect(formatCurrency(0)).toBe('$0.00')
  })

  it('formats small values with enough decimal places', () => {
    // minimumFractionDigits=2, maximumFractionDigits=4
    const result = formatCurrency(0.0012)
    expect(result).toBe('$0.0012')
  })

  it('formats an AUD amount', () => {
    const result = formatCurrency(2500, 'AUD')
    expect(result).toContain('2,500')
    // en-US locale uses A$ or AU$, just check numeric contents
  })

  it('rounds to 4 decimal places maximum', () => {
    const result = formatCurrency(1.123456)
    expect(result).toBe('$1.1235')
  })
})

describe('formatNumber', () => {
  it('formats a number with default 2 decimals', () => {
    expect(formatNumber(1234.5678)).toBe('1,234.57')
  })

  it('formats with custom decimal places', () => {
    expect(formatNumber(1234.5678, 4)).toBe('1,234.5678')
  })

  it('formats zero', () => {
    expect(formatNumber(0)).toBe('0.00')
  })

  it('adds thousands separator', () => {
    expect(formatNumber(1000000, 0)).toBe('1,000,000')
  })
})

describe('formatPercent', () => {
  it('formats a percentage to 2 decimal places', () => {
    expect(formatPercent(45.5)).toBe('45.50%')
  })

  it('formats zero percent', () => {
    expect(formatPercent(0)).toBe('0.00%')
  })

  it('formats 100 percent', () => {
    expect(formatPercent(100)).toBe('100.00%')
  })

  it('rounds correctly', () => {
    expect(formatPercent(33.3333)).toBe('33.33%')
  })
})
