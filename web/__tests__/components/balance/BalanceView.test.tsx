import React from 'react'
import { render, screen } from '../../test-utils'
import { BalanceView } from '@/components/balance/BalanceView'
import { useBalance, useEpochUsage } from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUseBalance = useBalance as jest.MockedFunction<typeof useBalance>
const mockUseEpochUsage = useEpochUsage as jest.MockedFunction<typeof useEpochUsage>

const balanceData = {
  diem: 45.5,
  usd: 11.25,
  daily_diem_limit: 100.0,
  daily_usd_limit: 25.0,
  diem_usage_percent: 45.5,
  usd_usage_percent: 45.0,
  next_epoch_begins: '2026-03-02T00:00:00Z',
}

const epochData = { diem: 8.123, usd: 2.01, bundled_credits: 0, epoch_start: '2026-03-01T00:00:00Z', next_epoch: '2026-03-02T00:00:00Z' }

describe('BalanceView — loading', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
    mockUseEpochUsage.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
  })

  it('shows loading indicator', () => {
    render(<BalanceView />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})

describe('BalanceView — success', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({ data: balanceData, isLoading: false, isError: false } as any)
    mockUseEpochUsage.mockReturnValue({ data: epochData, isLoading: false, isError: false } as any)
  })

  it('renders page heading', () => {
    render(<BalanceView />)
    expect(screen.getByRole('heading', { name: /balance & limits/i })).toBeInTheDocument()
  })

  it('renders Remaining Balance card title', () => {
    render(<BalanceView />)
    expect(screen.getByText('Remaining Balance')).toBeInTheDocument()
  })

  it('renders Epoch Consumption card title', () => {
    render(<BalanceView />)
    expect(screen.getByText('Epoch Consumption')).toBeInTheDocument()
  })

  it('renders DIEM balance value', () => {
    render(<BalanceView />)
    // formatNumber(45.5, 4) → "45.5000" (appears in Remaining Balance + Balance Summary)
    const els = screen.getAllByText('45.5000')
    expect(els.length).toBeGreaterThanOrEqual(1)
  })

  it('renders USD balance as currency', () => {
    render(<BalanceView />)
    const els = screen.getAllByText('$11.25')
    expect(els.length).toBeGreaterThanOrEqual(1)
  })

  it('renders DIEM consumed in usage section', () => {
    render(<BalanceView />)
    // formatNumber(8.123, 4) → "8.1230" (appears in Epoch Consumption + Balance Summary)
    const els = screen.getAllByText('8.1230')
    expect(els.length).toBeGreaterThanOrEqual(1)
  })

  it('renders USD consumed in usage section', () => {
    render(<BalanceView />)
    const els = screen.getAllByText('$2.01')
    expect(els.length).toBeGreaterThanOrEqual(1)
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
