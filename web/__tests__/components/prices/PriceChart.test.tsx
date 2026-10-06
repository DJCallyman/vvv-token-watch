import { fireEvent, render, screen } from '../../test-utils'
import { PriceChart } from '@/components/prices/PriceChart'
import { useAlertEvents, useAlerts, usePriceHistory } from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUsePriceHistory = usePriceHistory as jest.MockedFunction<typeof usePriceHistory>
const mockUseAlerts = useAlerts as jest.MockedFunction<typeof useAlerts>
const mockUseAlertEvents = useAlertEvents as jest.MockedFunction<typeof useAlertEvents>

const history = {
  token: 'vvv',
  range: '7d',
  count: 3,
  data: [
    { timestamp: '2026-01-01T00:00:00Z', token_id: 'vvv', price_usd: 100, price_aud: 150, market_cap: null, change_24h: null },
    { timestamp: '2026-01-01T06:00:00Z', token_id: 'vvv', price_usd: null, price_aud: null, market_cap: null, change_24h: null },
    { timestamp: '2026-01-01T12:00:00Z', token_id: 'vvv', price_usd: 110, price_aud: 165, market_cap: null, change_24h: null },
  ],
}

beforeEach(() => {
  jest.clearAllMocks()
  mockUsePriceHistory.mockReturnValue({ data: history, isLoading: false, isError: false } as any)
  mockUseAlerts.mockReturnValue({
    data: {
      alerts: [{ id: 1, name: 'pump', alert_type: 'rate_of_change', metric: 'vvv_price_usd' }],
      count: 1,
    },
  } as any)
  mockUseAlertEvents.mockReturnValue({
    data: {
      events: [
        {
          id: 7,
          alert_config_id: 1,
          triggered_at: '2026-01-01T12:00:00Z',
          message: 'pump: rate of change +9%',
          value: 110,
          acknowledged: false,
        },
      ],
      count: 1,
    },
  } as any)
})

describe('PriceChart analysis', () => {
  it('shows the documented volume limitation instead of synthesizing volume', () => {
    render(<PriceChart />)
    expect(screen.getByText(/volume unavailable/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Volume' })).toBeDisabled()
  })

  it('renders alert annotations linked to the matching event', () => {
    render(<PriceChart />)
    const link = screen.getByRole('link', { name: /rate of change/i })
    expect(link).toHaveAttribute('href', '/alerts#event-7')
  })

  it('offers indicator selection with sparse points', () => {
    render(<PriceChart />)
    fireEvent.change(screen.getByLabelText('Technical indicator'), { target: { value: 'sma7' } })
    expect(screen.getByLabelText('Technical indicator')).toHaveValue('sma7')
  })

  it('enables comparison mode with its own currency/time normalization note', () => {
    render(<PriceChart />)
    fireEvent.click(screen.getByLabelText('Compare with DIEM'))
    expect(mockUsePriceHistory).toHaveBeenCalledWith('diem', '7d')
  })
})
