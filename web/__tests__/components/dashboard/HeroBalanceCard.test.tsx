import React from 'react'
import { render, screen } from '@testing-library/react'
import { HeroBalanceCard } from '@/components/dashboard/HeroBalanceCard'
import { useBalance } from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUseBalance = useBalance as jest.MockedFunction<typeof useBalance>

const balanceData = {
  diem: 45.5,
  usd: 11.25,
  daily_diem_limit: 100.0,
  daily_usd_limit: 25.0,
  diem_usage_percent: 45.5,
  usd_usage_percent: 45.0,
  next_epoch_begins: '2026-03-02T00:00:00Z',
}

describe('HeroBalanceCard — loading', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as any)
  })

  it('shows loading text', () => {
    render(<HeroBalanceCard />)
    expect(screen.getByText(/loading balance/i)).toBeInTheDocument()
  })
})

describe('HeroBalanceCard — error', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as any)
  })

  it('shows error text', () => {
    render(<HeroBalanceCard />)
    expect(screen.getByText(/failed to load balance/i)).toBeInTheDocument()
  })
})

describe('HeroBalanceCard — success', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({
      data: balanceData,
      isLoading: false,
      isError: false,
    } as any)
  })

  it('renders the card title', () => {
    render(<HeroBalanceCard />)
    expect(screen.getByText('Account Balance')).toBeInTheDocument()
  })

  it('renders DIEM balance label', () => {
    render(<HeroBalanceCard />)
    expect(screen.getByText('DIEM Balance')).toBeInTheDocument()
  })

  it('renders DIEM numeric value', () => {
    render(<HeroBalanceCard />)
    // formatNumber(45.5, 2) → "45.50"
    expect(screen.getByText('45.50')).toBeInTheDocument()
  })

  it('renders USD balance label', () => {
    render(<HeroBalanceCard />)
    expect(screen.getByText('USD Balance')).toBeInTheDocument()
  })

  it('renders USD currency value', () => {
    render(<HeroBalanceCard />)
    // formatCurrency(11.25) → "$11.25"
    expect(screen.getByText('$11.25')).toBeInTheDocument()
  })

  it('renders usage percentage for DIEM', () => {
    render(<HeroBalanceCard />)
    // 45.5% usage displayed as "45.5%"
    const percentageEls = screen.getAllByText(/45\.5%/)
    expect(percentageEls.length).toBeGreaterThan(0)
  })

  it('shows high-usage warning style when usage > 80%', () => {
    mockUseBalance.mockReturnValue({
      data: { ...balanceData, diem_usage_percent: 90.0, usd_usage_percent: 90.0 },
      isLoading: false,
      isError: false,
    } as any)
    render(<HeroBalanceCard />)
    const highUsageEls = screen.getAllByText('90.0%')
    expect(highUsageEls.length).toBeGreaterThan(0)
    // The usage text should have destructive class
    highUsageEls.forEach(el => {
      expect(el.className).toMatch(/destructive/)
    })
  })

  it('renders daily DIEM limit', () => {
    render(<HeroBalanceCard />)
    // Daily Limit label appears twice (DIEM and USD sections)
    const limitLabels = screen.getAllByText('Daily Limit')
    expect(limitLabels.length).toBe(2)
  })
})
