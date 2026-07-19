import React from 'react'
import { render, screen } from '../../test-utils'
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

  it('renders DIEM label', () => {
    render(<HeroBalanceCard />)
    // Current implementation shows just "DIEM" (not "DIEM Balance")
    expect(screen.getByText('DIEM')).toBeInTheDocument()
  })

  it('renders DIEM numeric value with 4 decimals', () => {
    render(<HeroBalanceCard />)
    // formatNumber(45.5, 4) → "45.5000"
    expect(screen.getByText('45.5000')).toBeInTheDocument()
  })

  it('renders USD label', () => {
    render(<HeroBalanceCard />)
    expect(screen.getByText('USD')).toBeInTheDocument()
  })

  it('renders USD currency value', () => {
    render(<HeroBalanceCard />)
    expect(screen.getByText('$11.25')).toBeInTheDocument()
  })

  it('renders epoch reset info when next_epoch_begins is present', () => {
    render(<HeroBalanceCard />)
    expect(screen.getByText(/Epoch resets:/i)).toBeInTheDocument()
  })

  it('does not render usage percentages (moved to other views)', () => {
    render(<HeroBalanceCard />)
    // HeroBalanceCard no longer shows % usage; those live in BalanceView / TodayUsageCard
    expect(screen.queryByText(/45\.5%/)).not.toBeInTheDocument()
  })
})
