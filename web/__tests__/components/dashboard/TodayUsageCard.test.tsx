import React from 'react'
import { render, screen } from '@testing-library/react'
import { TodayUsageCard } from '@/components/dashboard/TodayUsageCard'
import { useEpochUsage } from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUseEpochUsage = useEpochUsage as jest.MockedFunction<typeof useEpochUsage>

const epochData = {
  diem: 12.3456,
  usd: 3.07,
  bundled_credits: 0,
  epoch_start: '2026-03-01T00:00:00Z',
  next_epoch: '2026-03-02T00:00:00Z',
}

describe('TodayUsageCard — loading', () => {
  beforeEach(() => {
    mockUseEpochUsage.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
  })

  it('shows loading placeholder', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})

describe('TodayUsageCard — error', () => {
  beforeEach(() => {
    mockUseEpochUsage.mockReturnValue({ data: undefined, isLoading: false, isError: true } as any)
  })

  it('shows error message', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText(/failed to load usage/i)).toBeInTheDocument()
  })
})

describe('TodayUsageCard — success', () => {
  beforeEach(() => {
    mockUseEpochUsage.mockReturnValue({ data: epochData, isLoading: false, isError: false } as any)
  })

  it('renders the card title', () => {
    render(<TodayUsageCard />)
    // BUG-02: now shows epoch title
    expect(screen.getByText(/This Epoch/i)).toBeInTheDocument()
  })

  it('renders DIEM consumed label', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText('DIEM Consumed')).toBeInTheDocument()
  })

  it('renders DIEM usage value to 4 decimal places', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText('12.3456')).toBeInTheDocument()
  })

  it('renders USD consumed label', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText('USD Consumed')).toBeInTheDocument()
  })

  it('renders USD usage as currency', () => {
    render(<TodayUsageCard />)
    expect(screen.getByText('$3.07')).toBeInTheDocument()
  })

  it('renders zero DIEM correctly', () => {
    mockUseEpochUsage.mockReturnValue({
      data: { diem: 0, usd: 0, bundled_credits: 0, epoch_start: null, next_epoch: null },
      isLoading: false,
      isError: false,
    } as any)
    render(<TodayUsageCard />)
    expect(screen.getByText('0.0000')).toBeInTheDocument()
  })
})
