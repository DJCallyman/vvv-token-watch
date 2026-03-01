import React from 'react'
import { render, screen } from '@testing-library/react'
import { Header } from '@/components/layout/Header'
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

describe('Header — loading', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
  })

  it('renders without crashing while loading', () => {
    render(<Header />)
    // The spinner (RefreshCw) should be visible during loading
    const header = screen.getByRole('banner')
    expect(header).toBeInTheDocument()
  })

  it('renders Connected badge (not yet errored)', () => {
    render(<Header />)
    expect(screen.getByText('Connected')).toBeInTheDocument()
  })

  it('does not show balance values while loading', () => {
    render(<Header />)
    expect(screen.queryByText('DIEM Balance')).not.toBeInTheDocument()
  })
})

describe('Header — error', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({ data: undefined, isLoading: false, isError: true } as any)
  })

  it('renders Disconnected badge on error', () => {
    render(<Header />)
    expect(screen.getByText('Disconnected')).toBeInTheDocument()
  })

  it('does not show balance values on error', () => {
    render(<Header />)
    expect(screen.queryByText('DIEM Balance')).not.toBeInTheDocument()
  })
})

describe('Header — success', () => {
  beforeEach(() => {
    mockUseBalance.mockReturnValue({ data: balanceData, isLoading: false, isError: false } as any)
  })

  it('renders Connected badge', () => {
    render(<Header />)
    expect(screen.getByText('Connected')).toBeInTheDocument()
  })

  it('renders DIEM Balance label', () => {
    render(<Header />)
    expect(screen.getByText('DIEM Balance')).toBeInTheDocument()
  })

  it('renders DIEM numeric balance', () => {
    render(<Header />)
    // formatNumber(45.5, 2) → "45.50"
    expect(screen.getByText('45.50')).toBeInTheDocument()
  })

  it('renders USD Balance label', () => {
    render(<Header />)
    expect(screen.getByText('USD Balance')).toBeInTheDocument()
  })

  it('renders USD currency balance', () => {
    render(<Header />)
    // formatCurrency(11.25) → "$11.25"
    expect(screen.getByText('$11.25')).toBeInTheDocument()
  })
})
