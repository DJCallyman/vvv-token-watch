import React from 'react'
import { render, screen } from '@testing-library/react'
import { TodayUsageCard } from '@/components/dashboard/TodayUsageCard'
import { useDailyUsage } from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUseDailyUsage = useDailyUsage as jest.MockedFunction<typeof useDailyUsage>

const usageData = { diem: 12.3456, usd: 3.07, date: '2026-03-01' }

describe('TodayUsageCard — loading', () => {
  beforeEach(() => {
    mockUseDailyUsage.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
  })

  it('shows loading placeholder', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})

describe('TodayUsageCard — error', () => {
  beforeEach(() => {
    mockUseDailyUsage.mockReturnValue({ data: undefined, isLoading: false, isError: true } as any)
  })

  it('shows error message', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText(/failed to load usage/i)).toBeInTheDocument()
  })
})

describe('TodayUsageCard — success', () => {
  beforeEach(() => {
    mockUseDailyUsage.mockReturnValue({ data: usageData, isLoading: false, isError: false } as any)
  })

  it('renders the card title', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText("Today's Usage")).toBeInTheDocument()
  })

  it('renders DIEM consumed label', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText('DIEM Consumed')).toBeInTheDocument()
  })

  it('renders DIEM usage value to 4 decimal places', () => {
    render(<TodayUsageCard />)
    // formatNumber(12.3456, 4) → "12.3456"
    expect(screen.getByText('12.3456')).toBeInTheDocument()
  })

  it('renders USD consumed label', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText('USD Consumed')).toBeInTheDocument()
  })

  it('renders USD usage as currency', () => {
    render(<TodayUsageCard />)
    // formatCurrency(3.07) → "$3.07"
    expect(screen.getByText('$3.07')).toBeInTheDocument()
  })

  it('renders zero DIEM correctly', () => {
    mockUseDailyUsage.mockReturnValue({
      data: { diem: 0, usd: 0, date: '2026-03-01' },
      isLoading: false,
      isError: false,
    } as any)
    render(<TodayUsageCard />)
    expect(screen.getByText('0.0000')).toBeInTheDocument()
  })
})
