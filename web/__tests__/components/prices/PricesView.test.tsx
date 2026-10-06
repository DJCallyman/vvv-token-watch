import React from 'react'
import { fireEvent, render, screen } from '../../test-utils'
import { PricesView } from '@/components/prices/PricesView'
import { useAlertEvents, useAlerts, usePrices, usePriceHistory, useUpdateSettings } from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUsePrices = usePrices as jest.MockedFunction<typeof usePrices>
const mockUsePriceHistory = usePriceHistory as jest.MockedFunction<typeof usePriceHistory>
const mockUseUpdateSettings = useUpdateSettings as jest.MockedFunction<typeof useUpdateSettings>
const mockUseAlerts = useAlerts as jest.MockedFunction<typeof useAlerts>
const mockUseAlertEvents = useAlertEvents as jest.MockedFunction<typeof useAlertEvents>

beforeEach(() => {
  mockUseAlerts.mockReturnValue({ data: { alerts: [], count: 0 } } as any)
  mockUseAlertEvents.mockReturnValue({ data: { events: [], count: 0 } } as any)
})

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

const priceHistoryData = {
  data: [],
  count: 0,
}

describe('PricesView — loading', () => {
  beforeEach(() => {
    mockUsePrices.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
    mockUsePriceHistory.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
    mockUseUpdateSettings.mockReturnValue({ mutate: jest.fn(), isPending: false } as any)
  })

  it('shows loading text', () => {
    render(<PricesView />)
    expect(screen.getByText('Loading token prices').closest('[aria-live="polite"]')).toHaveAttribute('aria-busy', 'true')
  })
})

describe('PricesView — error', () => {
  beforeEach(() => {
    mockUsePrices.mockReturnValue({ data: undefined, isLoading: false, isError: true, refetch: jest.fn() } as any)
    mockUsePriceHistory.mockReturnValue({ data: undefined, isLoading: false, isError: false } as any)
    mockUseUpdateSettings.mockReturnValue({ mutate: jest.fn(), isPending: false } as any)
  })

  it('shows a retryable error state', () => {
    render(<PricesView />)
    expect(screen.getByRole('heading', { name: /could not load token prices/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })
})

describe('PricesView — success', () => {
  beforeEach(() => {
    mockUsePrices.mockReturnValue({ data: pricesData, isLoading: false, isError: false } as any)
    mockUsePriceHistory.mockReturnValue({ data: priceHistoryData, isLoading: false, isError: false } as any)
    mockUseUpdateSettings.mockReturnValue({ mutate: jest.fn(), isPending: false } as any)
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

  it('persists the selected display currency', () => {
    const mutate = jest.fn()
    mockUseUpdateSettings.mockReturnValue({ mutate, isPending: false } as any)

    render(<PricesView />)
    fireEvent.change(screen.getByRole('combobox', { name: 'Portfolio currency' }), {
      target: { value: 'AUD' },
    })

    expect(mutate).toHaveBeenCalledWith({ display_currency: 'AUD' })
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

  it('renders portfolio VVV value', () => {
    render(<PricesView />)
    expect(screen.getByText('$6,875.00')).toBeInTheDocument()
  })

  it('values the full wallet position in USD, not just unstaked VVV', () => {
    // Wallet source: holdings.vvv = 100 unstaked + 200 sVVV + 5 rewards.
    // The API's portfolio.vvv_value_usd only covers the 100 unstaked VVV.
    mockUsePrices.mockReturnValue({
      data: {
        vvv: { usd: 2.5, aud: 3.85 },
        diem: { usd: 0.01, aud: 0.015 },
        holdings: { vvv: 305, diem: 4 },
        portfolio: {
          vvv_value_usd: 250,
          svvv_value_usd: 500,
          unclaimed_rewards_value_usd: 12.5,
          diem_value_usd: 0.04,
          total_usd: 762.54,
        },
      },
      isLoading: false,
      isError: false,
    } as any)

    render(<PricesView />)

    // 305 * 2.50 = 762.50 in both the holdings line and the portfolio tile.
    expect(screen.getAllByText('$762.50').length).toBeGreaterThan(0)
    // The wallet-only subtotal must not be shown as the total.
    expect(screen.queryByText('$250.00')).not.toBeInTheDocument()
  })

  it('renders portfolio DIEM value', () => {
    render(<PricesView />)
    // formatCurrency(5.0) → "$5.00"
    expect(screen.getByText('$5.00')).toBeInTheDocument()
  })

  it('still renders Portfolio Summary (with fallback calc) when portfolio data is absent', () => {
    mockUsePrices.mockReturnValue({
      data: { ...pricesData, portfolio: undefined },
      isLoading: false,
      isError: false,
    } as any)
    render(<PricesView />)
    // Current component always renders the section and falls back to holdings * price
    expect(screen.getByText('Portfolio Summary')).toBeInTheDocument()
    // 2750 * 2.50 = 6875, 500 * 0.01 = 5
    expect(screen.getByText('$6,875.00')).toBeInTheDocument()
    expect(screen.getByText('$5.00')).toBeInTheDocument()
  })
})
