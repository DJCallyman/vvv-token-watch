import React from 'react'
import { render, screen } from '@testing-library/react'
import { BalanceView } from '@/components/balance/BalanceView'
import { useBalance, useDailyUsage } from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUseBalance = useBalance as jest.MockedFunction<typeof useBalance>
const mockUseDailyUsage = useDailyUsage as jest.MockedFunction<typeof useDailyUsage>

const balanceData = {
  diem: 45.5,
  usd: 11.25,
  daily_diem_limit: 100.0,
  daily_usd_limit: 25.0,
  diem_usage_percent: 45.5,
  usd_usage_percent: 45.0,
  next_epoch_begins: '2026-03-02T00:00:00Z',
}

const usageData = { diem: 8.123, usd: 2.01, date: '2026-03-01' }

describe('BalanceView — loading', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
    mockUseDailyUsage.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
  })

  it('shows loading indicator', () => {
    render(<BalanceView />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})

describe('BalanceView — success', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({ data: balanceData, isLoading: false, isError: false } as any)
    mockUseDailyUsage.mockReturnValue({ data: usageData, isLoading: false, isError: false } as any)
  })

  it('renders page heading', () => {
    render(<BalanceView />)
    expect(screen.getByRole('heading', { name: /balance & limits/i })).toBeInTheDocument()
  })

  it('renders Current Balance card title', () => {
    render(<BalanceView />)
    expect(screen.getByText('Current Balance')).toBeInTheDocument()
  })

  it("renders Today's Usage card title", () => {
    render(<BalanceView />)
    expect(screen.getByText("Today's Usage")).toBeInTheDocument()
  })

  it('renders DIEM balance value', () => {
    render(<BalanceView />)
    // formatNumber(45.5, 4) → "45.5000"
    expect(screen.getByText('45.5000')).toBeInTheDocument()
  })

  it('renders USD balance as currency', () => {
    render(<BalanceView />)
    expect(screen.getByText('$11.25')).toBeInTheDocument()
  })

  it('renders DIEM consumed in usage section', () => {
    render(<BalanceView />)
    // formatNumber(8.123, 4) → "8.1230"
    expect(screen.getByText('8.1230')).toBeInTheDocument()
  })

  it('renders USD consumed in usage section', () => {
    render(<BalanceView />)
    expect(screen.getByText('$2.01')).toBeInTheDocument()
  })

  it('renders Epoch Information card when next_epoch_begins is present', () => {
    render(<BalanceView />)
    expect(screen.getByText('Epoch Information')).toBeInTheDocument()
    expect(screen.getByText('Next Epoch Begins')).toBeInTheDocument()
  })

  it('does not render epoch card when next_epoch_begins is absent', () => {
    mockUseBalance.mockReturnValue({
      data: { ...balanceData, next_epoch_begins: undefined },
      isLoading: false,
      isError: false,
    } as any)
    render(<BalanceView />)
    expect(screen.queryByText('Epoch Information')).not.toBeInTheDocument()
  })

  it('renders dash placeholders when balance data is null', () => {
    mockUseBalance.mockReturnValue({ data: undefined, isLoading: false, isError: false } as any)
    render(<BalanceView />)
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(2)
  })
})
