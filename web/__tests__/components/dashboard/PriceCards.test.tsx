import React from 'react'
import { render, screen } from '@testing-library/react'
import { PriceCards } from '@/components/dashboard/PriceCards'
import { usePrices } from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUsePrices = usePrices as jest.MockedFunction<typeof usePrices>

const pricesData = {
  vvv: { usd: 2.50, aud: 3.85 },
  diem: { usd: 0.01, aud: 0.015 },
  holdings: {
    vvv: 305,
    diem: 500,
    vvv_source: 'wallet' as const,
    diem_source: 'wallet' as const,
    vvv_wallet: 100,
    svvv: 200,
    unclaimed_rewards: 5,
    diem_wallet: 500,
    diem_staked: 0,
  },
  portfolio: {
    vvv_value_usd: 250.0,
    svvv_value_usd: 500.0,
    unclaimed_rewards_value_usd: 12.5,
    diem_value_usd: 5.0,
    gross_exposure_usd: 767.5,
    diem_unlock_offset_usd: 5.0,
    net_worth_usd: 762.5,
    total_usd: 767.5,
  },
}

describe('PriceCards — loading', () => {
  beforeEach(() => {
    mockUsePrices.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
  })

  it('renders loading placeholder cards', () => {
    render(<PriceCards />)
    const loaders = screen.getAllByText(/loading/i)
    expect(loaders.length).toBeGreaterThan(0)
  })
})

describe('PriceCards — error', () => {
  beforeEach(() => {
    mockUsePrices.mockReturnValue({ data: undefined, isLoading: false, isError: true } as any)
  })

  it('shows error message', () => {
    render(<PriceCards />)
    expect(screen.getByText(/failed to load prices/i)).toBeInTheDocument()
  })
})

describe('PriceCards — success', () => {
  beforeEach(() => {
    mockUsePrices.mockReturnValue({ data: pricesData, isLoading: false, isError: false } as any)
  })

  it('renders VVV Price card title', () => {
    render(<PriceCards />)
    expect(screen.getByText('VVV Price')).toBeInTheDocument()
  })

  it('renders DIEM Price card title', () => {
    render(<PriceCards />)
    expect(screen.getByText('DIEM Price')).toBeInTheDocument()
  })

  it('renders VVV USD price', () => {
    render(<PriceCards />)
    // formatCurrency(2.50) → "$2.50"
    expect(screen.getByText('$2.50')).toBeInTheDocument()
  })

  it('renders DIEM USD price', () => {
    render(<PriceCards />)
    // formatCurrency(0.01) → "$0.01"
    expect(screen.getByText('$0.01')).toBeInTheDocument()
  })

  it('renders Protocol Exposure card title', () => {
    render(<PriceCards />)
    expect(screen.getByText('Protocol Exposure')).toBeInTheDocument()
  })

  it('renders gross exposure and net worth', () => {
    render(<PriceCards />)
    expect(screen.getByText('$767.50')).toBeInTheDocument()
    expect(screen.getByText('$762.50')).toBeInTheDocument()
    expect(screen.getByText('sVVV')).toBeInTheDocument()
    expect(screen.getByText('Unclaimed Rewards')).toBeInTheDocument()
    expect(screen.getByText('Net worth')).toBeInTheDocument()
  })

  it('renders VVV AUD price when available', () => {
    render(<PriceCards />)
    // formatCurrency(3.85, 'AUD') in en-US locale renders as "A$3.85" (not "AUD ...")
    const audElements = screen.getAllByText(/3\.85/)
    expect(audElements.length).toBeGreaterThan(0)
  })

  it('does not show AUD price when missing', () => {
    mockUsePrices.mockReturnValue({
      data: { ...pricesData, vvv: { usd: 1.0 }, diem: { usd: 0.005 } },
      isLoading: false,
      isError: false,
    } as any)
    render(<PriceCards />)
    const audEls = screen.queryAllByText(/AUD/)
    expect(audEls.length).toBe(0)
  })
})
