import React from 'react'
import { render, screen } from '@testing-library/react'
import { PricesView } from '@/components/prices/PricesView'
import { usePrices } from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUsePrices = usePrices as jest.MockedFunction<typeof usePrices>

const pricesData = {
  vvv: { usd: 2.50, aud: 3.85 },
  diem: { usd: 0.01, aud: 0.015 },
  holdings: { vvv: 2750, diem: 500 },
  portfolio: {
    vvv_value_usd: 6875.0,
    diem_value_usd: 5.0,
    total_usd: 6880.0,
  },
}

describe('PricesView — loading', () => {
  beforeEach(() => {
    mockUsePrices.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
  })

  it('shows loading text', () => {
    render(<PricesView />)
    expect(screen.getByText(/loading prices/i)).toBeInTheDocument()
  })
})

describe('PricesView — error', () => {
  beforeEach(() => {
    mockUsePrices.mockReturnValue({ data: undefined, isLoading: false, isError: true } as any)
  })

  it('shows error message', () => {
    render(<PricesView />)
    expect(screen.getByText(/failed to load prices/i)).toBeInTheDocument()
  })
})

describe('PricesView — success', () => {
  beforeEach(() => {
    mockUsePrices.mockReturnValue({ data: pricesData, isLoading: false, isError: false } as any)
  })

  it('renders page heading', () => {
    render(<PricesView />)
    expect(screen.getByRole('heading', { name: /token prices/i })).toBeInTheDocument()
  })

  it('renders VVV Token card', () => {
    render(<PricesView />)
    expect(screen.getByText('VVV Token')).toBeInTheDocument()
  })

  it('renders DIEM Token card', () => {
    render(<PricesView />)
    expect(screen.getByText('DIEM Token')).toBeInTheDocument()
  })

  it('renders VVV USD price', () => {
    render(<PricesView />)
    expect(screen.getByText('$2.50')).toBeInTheDocument()
  })

  it('renders DIEM USD price', () => {
    render(<PricesView />)
    expect(screen.getByText('$0.01')).toBeInTheDocument()
  })

  it('renders VVV AUD price', () => {
    render(<PricesView />)
    // formatCurrency(3.85, 'AUD') in en-US locale → "A$3.85" (not the literal string "AUD")
    const audElements = screen.getAllByText(/3\.85/)
    expect(audElements.length).toBeGreaterThan(0)
  })

  it('renders VVV holdings amount', () => {
    render(<PricesView />)
    // formatNumber(2750) → "2,750.00"
    expect(screen.getByText('2,750.00 VVV')).toBeInTheDocument()
  })

  it('renders DIEM holdings amount', () => {
    render(<PricesView />)
    // formatNumber(500) → "500.00"
    expect(screen.getByText('500.00 DIEM')).toBeInTheDocument()
  })

  it('renders Portfolio Summary card', () => {
    render(<PricesView />)
    expect(screen.getByText('Portfolio Summary')).toBeInTheDocument()
  })

  it('renders portfolio total value', () => {
    render(<PricesView />)
    expect(screen.getByText('$6,880.00')).toBeInTheDocument()
  })

  it('renders portfolio VVV value', () => {
    render(<PricesView />)
    expect(screen.getByText('$6,875.00')).toBeInTheDocument()
  })

  it('renders portfolio DIEM value', () => {
    render(<PricesView />)
    // formatCurrency(5.0) → "$5.00"
    expect(screen.getByText('$5.00')).toBeInTheDocument()
  })

  it('does not render portfolio section when portfolio is absent', () => {
    mockUsePrices.mockReturnValue({
      data: { ...pricesData, portfolio: undefined },
      isLoading: false,
      isError: false,
    } as any)
    render(<PricesView />)
    expect(screen.queryByText('Portfolio Summary')).not.toBeInTheDocument()
  })
})
